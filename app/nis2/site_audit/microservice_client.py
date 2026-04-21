"""
NIS2 Microservice Client
=========================
REST client for the Docker-based NIS2/DSGVO pentesting microservice.

The microservice runs full pentesting tools (nmap, nuclei, testssl.sh,
nikto, subfinder, httpx, dns_audit, cookie_check) + Claude AI analysis.

Environment variables:
  NIS2_MICROSERVICE_URL      – base URL, e.g. http://187.124.6.120:5000
  NIS2_MICROSERVICE_API_KEY  – value for X-API-Key header
  NIS2_MICROSERVICE_TIMEOUT  – per-request HTTP timeout in seconds (default 30)

Endpoints used:
  GET  /api/health                     – public health check
  POST /api/audit                      – start audit → {"job_id": N}
  GET  /api/audit/<id>                 – status: pending|running|done|failed
  GET  /api/audit/<id>/findings        – findings list
  GET  /api/audit/<id>/logs?after=<N>  – paginated log stream
"""

from __future__ import annotations

import logging
import os
import time
from typing import Callable, List, Tuple

import requests

logger = logging.getLogger(__name__)

_URL = os.environ.get("NIS2_MICROSERVICE_URL", "").rstrip("/")
_KEY = os.environ.get("NIS2_MICROSERVICE_API_KEY", "")
_HTTP_TIMEOUT = int(os.environ.get("NIS2_MICROSERVICE_TIMEOUT", "30"))

_SEVERITY_RANK: dict[str, int] = {
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
    "info": 5,
}


# ──────────────────────────────────────────────────────────────────
# Public helpers
# ──────────────────────────────────────────────────────────────────

def is_configured() -> bool:
    """Return True if the microservice URL and API key are set in env."""
    return bool(_URL and _KEY)


def health_check() -> bool:
    """Quick liveness check — returns True when microservice is reachable."""
    if not is_configured():
        return False
    try:
        r = requests.get(f"{_URL}/api/health", timeout=5)
        return r.status_code == 200 and r.json().get("ok") is True
    except Exception as exc:
        logger.warning("NIS2 microservice health check failed: %s", exc)
        return False


# ──────────────────────────────────────────────────────────────────
# Low-level API calls
# ──────────────────────────────────────────────────────────────────

def _headers() -> dict:
    return {"X-API-Key": _KEY, "Content-Type": "application/json"}


def _start_audit(target: str, company: str) -> int:
    """POST /api/audit → microservice job_id (integer)."""
    r = requests.post(
        f"{_URL}/api/audit",
        headers=_headers(),
        json={"target": target, "company": company},
        timeout=_HTTP_TIMEOUT,
    )
    r.raise_for_status()
    return int(r.json()["job_id"])


def _get_status(remote_id: int) -> dict:
    """GET /api/audit/<id> → status dict."""
    r = requests.get(
        f"{_URL}/api/audit/{remote_id}",
        headers=_headers(),
        timeout=_HTTP_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def _get_findings(remote_id: int) -> List[dict]:
    """GET /api/audit/<id>/findings → list of finding dicts."""
    r = requests.get(
        f"{_URL}/api/audit/{remote_id}/findings",
        headers=_headers(),
        timeout=_HTTP_TIMEOUT,
    )
    r.raise_for_status()
    return r.json().get("findings", [])


def _get_new_logs(remote_id: int, after: int = 0) -> List[dict]:
    """GET /api/audit/<id>/logs?after=N → new log entries since last poll."""
    r = requests.get(
        f"{_URL}/api/audit/{remote_id}/logs",
        headers=_headers(),
        params={"after": after},
        timeout=_HTTP_TIMEOUT,
    )
    r.raise_for_status()
    return r.json().get("logs", [])


# ──────────────────────────────────────────────────────────────────
# High-level orchestration
# ──────────────────────────────────────────────────────────────────

def run_audit_with_polling(
    target: str,
    company: str,
    log_fn: Callable[[str, str], None],
    poll_interval: int = 10,
    max_wait_seconds: int = 2400,  # 40 minutes — nuclei + nikto are slow
) -> Tuple[str, List[dict]]:
    """
    Full microservice audit lifecycle.

    1. Start remote audit, receive job_id
    2. Poll status every `poll_interval` seconds
    3. Continuously stream logs back via log_fn(level, message)
    4. Fetch and return findings when complete

    Returns:
        (status, findings) where
        status  : 'done' | 'failed' | 'timeout'
        findings: list of dicts with keys:
                  title, description, severity, severity_rank,
                  cvss, dsgvo_article, recommendation, tool
    """
    if not is_configured():
        log_fn("ERROR", "NIS2_MICROSERVICE_URL / API_KEY nicht konfiguriert.")
        return "failed", []

    log_fn("INFO", f"🚀 Starte vollständigen NIS2/DSGVO Sicherheits-Pentest: {target}")
    log_fn("INFO", "🔧 Tools: nmap · nuclei · testssl · nikto · subfinder · httpx · dns_audit · cookie_check")

    # Step 1 — start
    try:
        remote_id = _start_audit(target, company)
        log_fn("INFO", f"✅ Audit-Job #{remote_id} auf Pentest-Server gestartet")
    except Exception as exc:
        log_fn("ERROR", f"Microservice nicht erreichbar: {exc}")
        return "failed", []

    last_log_id = 0
    elapsed = 0

    # Step 2 — poll
    while elapsed < max_wait_seconds:
        time.sleep(poll_interval)
        elapsed += poll_interval

        # Fetch new log lines
        try:
            new_logs = _get_new_logs(remote_id, after=last_log_id)
            for entry in new_logs:
                log_fn(entry.get("level", "INFO"), entry.get("message", ""))
                last_log_id = max(last_log_id, entry.get("id", 0))
        except Exception as exc:
            log_fn("INFO", f"Log-Polling (nicht kritisch): {exc}")

        # Check completion
        try:
            status_data = _get_status(remote_id)
            status = status_data.get("status", "running")
        except Exception as exc:
            log_fn("INFO", f"Status-Abfrage fehlgeschlagen: {exc}")
            continue

        if status == "done":
            count = status_data.get("findings_count", 0)
            log_fn("INFO", f"✅ Pentest abgeschlossen — {count} Sicherheitsbefunde")
            try:
                findings = _get_findings(remote_id)
                # Normalise severity_rank
                for f in findings:
                    f["severity_rank"] = _SEVERITY_RANK.get(
                        (f.get("severity") or "info").lower(), 5
                    )
            except Exception as exc:
                log_fn("ERROR", f"Befunde konnten nicht geladen werden: {exc}")
                findings = []
            return "done", findings

        if status == "failed":
            log_fn("ERROR", "❌ Pentest auf Microservice fehlgeschlagen.")
            return "failed", []

        # Still running — log progress every 60s
        if elapsed % 60 == 0:
            log_fn("INFO", f"⏳ Pentest läuft … ({elapsed}s vergangen)")

    log_fn("ERROR", f"⏰ Timeout nach {max_wait_seconds}s — Audit nicht abgeschlossen.")
    return "timeout", []
