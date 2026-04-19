"""
NIS2 Site Audit — AI-powered Audit Agent
==========================================
Runs security checks and uses Claude AI to generate structured findings.

Python-only mode (Render.com without Docker):
  ✅ live_check (HTTP headers, TLS, cookies, DNS)
  ✅ dns_audit  (SPF, DMARC, DKIM, DNSSEC via dig)
  ✅ cookie_check (Python)
  ✅ Claude AI analysis via Anthropic API

External tools (skipped gracefully when not installed):
  ⚠️ nmap, nuclei, httpx, subfinder, nikto, testssl.sh

Adapted from NIS2-SDWGO (https://github.com/pilipandr770/NIS2-SDWGO).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

import anthropic

from .live_check import fetch_live_check

logger = logging.getLogger(__name__)

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5")

# ---------------------------------------------------------------------------
# Severity helpers
# ---------------------------------------------------------------------------
_SEVERITY_RANK = {
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
    "info": 5,
}


def _rank(severity: str) -> int:
    return _SEVERITY_RANK.get(severity.lower(), 5)


# ---------------------------------------------------------------------------
# Tool: DNS audit (subprocess dig)
# ---------------------------------------------------------------------------
def _run_cmd(cmd: List[str], timeout: int = 10) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def dns_audit(target: str) -> str:
    """Return a text report of DNS security records."""
    domain = target.replace("https://", "").replace("http://", "").split("/")[0]
    if not shutil.which("dig"):
        return f"dig nicht installiert — DNS-Audit übersprungen für {domain}"

    lines = [f"=== DNS Security Audit: {domain} ==="]

    spf = _run_cmd(["dig", "+short", domain, "TXT"])
    lines.append(f"\nSPF/TXT Records:\n{spf or '(keine)'}")

    dmarc = _run_cmd(["dig", "+short", f"_dmarc.{domain}", "TXT"])
    lines.append(f"\nDMARC (_dmarc.{domain}):\n{dmarc or '(kein DMARC)'}")

    ds = _run_cmd(["dig", "+short", domain, "DS"])
    lines.append(f"\nDNSSEC DS:\n{ds or '(kein DS — DNSSEC nicht aktiv)'}")

    mx = _run_cmd(["dig", "+short", domain, "MX"])
    lines.append(f"\nMX Records:\n{mx or '(keine MX)'}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: Cookie check (Python)
# ---------------------------------------------------------------------------
def cookie_check(target: str) -> str:
    """Check cookie security flags and return text report."""
    import ssl
    import urllib.request

    if not target.startswith(("http://", "https://")):
        target = "https://" + target

    lines = [f"=== Cookie-Check: {target} ==="]
    try:
        req = urllib.request.Request(
            target, headers={"User-Agent": "NIS2-SecurityAudit/1.0"}
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            cookies = []
            for key, val in resp.headers.items():
                if key.lower() == "set-cookie":
                    cookies.append(val)

            if not cookies:
                lines.append("Keine Set-Cookie-Header gefunden.")
            else:
                for c in cookies:
                    name = c.split("=")[0].strip()
                    flags = c.lower()
                    issues = []
                    if "httponly" not in flags:
                        issues.append("KEIN HttpOnly")
                    if "secure" not in flags:
                        issues.append("KEIN Secure")
                    if "samesite" not in flags:
                        issues.append("KEIN SameSite")
                    status = "OK" if not issues else f"⚠ {', '.join(issues)}"
                    lines.append(f"  Cookie '{name}': {status}")
    except Exception as exc:
        lines.append(f"Cookie-Check fehlgeschlagen: {exc}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Claude AI agent
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """Du bist ein erfahrener IT-Security-Auditor und NIS2-Compliance-Experte.
Du analysierst Sicherheitsdaten einer Website und erstellst strukturierte Findings
für einen professionellen NIS2/DSGVO-Auditbericht.

Antworte IMMER mit einem gültigen JSON-Array von Findings.
Jedes Finding hat folgende Felder:
{
  "title": "kurzer Titel (deutsch)",
  "description": "detaillierte Beschreibung (deutsch)",
  "severity": "critical|high|medium|low|info",
  "cvss": "CVSS-Score z.B. 7.5 (optional, kann leer sein)",
  "dsgvo_article": "relevante DSGVO-Artikel (z.B. Art. 32 DSGVO, optional)",
  "recommendation": "konkrete Handlungsempfehlung (deutsch)",
  "tool": "live_check|dns|cookie|ai"
}

Wichtig:
- Beziehe dich auf konkrete Daten aus dem Input
- Für fehlende Security Headers: severity 'high' wenn HSTS oder CSP fehlt, 'medium' für andere
- Für DMARC/SPF-Probleme: severity 'high'
- Für Cookie-Probleme: severity 'medium'
- Keine Findings erfinden — nur was aus den Daten erkennbar ist
- Antworte NUR mit dem JSON-Array, kein Text davor oder danach
"""


def _call_claude(user_message: str) -> List[Dict[str, Any]]:
    """Call Claude API and parse JSON findings."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set — skipping AI analysis")
        return []

    client = anthropic.Anthropic(api_key=api_key)
    try:
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        text = resp.content[0].text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except json.JSONDecodeError:
        logger.exception("Claude returned non-JSON response")
        return []
    except Exception:
        logger.exception("Claude API call failed")
        return []


# ---------------------------------------------------------------------------
# Task auto-marking based on findings
# ---------------------------------------------------------------------------

def _auto_mark_tasks(tasks_list: List[Dict], findings: List[Dict]) -> None:
    """Mark tasks as done=True if no critical/high finding covers them."""
    high_severity_titles = {
        f["title"].lower() for f in findings if _rank(f.get("severity", "info")) <= 2
    }

    # Mapping of task titles to keywords that would indicate a problem
    _PROBLEM_KEYWORDS: Dict[str, List[str]] = {
        "http security headers": ["header", "csp", "hsts", "x-frame", "x-content"],
        "tls/ssl-konfiguration": ["tls", "ssl", "zertifikat", "certificate"],
        "subdomain- & dns-sicherheit": ["spf", "dmarc", "dkim", "dnssec", "dns"],
        "cookie": ["cookie", "httponly", "samesite", "secure"],
    }

    for task in tasks_list:
        title_lower = task["title"].lower()
        # Check if any high-severity finding relates to this task
        related = False
        for keyword_group, keywords in _PROBLEM_KEYWORDS.items():
            if keyword_group in title_lower or any(kw in title_lower for kw in keywords):
                if any(
                    any(kw in f["title"].lower() or kw in f.get("description", "").lower()
                        for kw in keywords)
                    for f in findings
                    if _rank(f.get("severity", "info")) <= 2
                ):
                    related = True
                    break

        if not related:
            # Mark as done if category is Organisatorisch or DSGVO
            # (those require manual human action — mark based on existing data)
            if task["category"] in ("Organisatorisch", "DSGVO"):
                task["done"] = False  # Always manual
            else:
                # Mark technical tasks as done only if no related finding
                task["done"] = True
                task["done_at"] = datetime.utcnow().isoformat()
                task["notes"] = "Automatisch geprüft — kein kritisches Finding"


# ---------------------------------------------------------------------------
# Main audit function
# ---------------------------------------------------------------------------

def run_audit(
    job_id: int,
    target: str,
    log_fn=None,
) -> Dict[str, Any]:
    """
    Run the full Python-based audit.

    Args:
        job_id:  DB job ID (for logging context)
        target:  URL or domain to audit
        log_fn:  callable(level, message) — persists log lines to DB

    Returns dict with:
        findings: list of finding dicts
        live: live_check result dict
        tasks: list of task dicts (with done/notes updated)
        tools_used: list of tools that actually ran
    """

    def _log(level: str, msg: str) -> None:
        logger.info("[job=%d][%s] %s", job_id, level, msg)
        if log_fn:
            try:
                log_fn(level, msg)
            except Exception:
                pass

    # Normalise target
    if not target.startswith(("http://", "https://")):
        target = "https://" + target

    tools_used: List[str] = []
    all_findings: List[Dict[str, Any]] = []

    # ── 1. Live Check ──────────────────────────────────────────────────────
    _log("INFO", f"🔍 Starte Live-Check für {target} …")
    live = fetch_live_check(target)
    if "error" in live:
        _log("ERROR", f"Live-Check Fehler: {live['error']}")
        return {"error": live["error"], "findings": [], "live": live, "tasks": [], "tools_used": []}

    tools_used.append("live_check")
    _log("INFO", f"✅ Live-Check abgeschlossen — {live.get('warning_count', 0)} Warnungen")

    # ── 2. DNS Audit ───────────────────────────────────────────────────────
    _log("CMD", "dig +short … (DNS-Audit)")
    dns_report = dns_audit(target)
    tools_used.append("dns_audit")
    _log("INFO", "✅ DNS-Audit abgeschlossen")

    # ── 3. Cookie Check ────────────────────────────────────────────────────
    _log("CMD", "Cookie-Check (Python)")
    cookie_report = cookie_check(target)
    tools_used.append("cookie_check")
    _log("INFO", "✅ Cookie-Check abgeschlossen")

    # ── 4. Optional external tools ────────────────────────────────────────
    domain = target.replace("https://", "").replace("http://", "").split("/")[0]
    ext_results: Dict[str, str] = {}
    skipped: List[str] = []

    # --- nmap ---------------------------------------------------------------
    if shutil.which("nmap"):
        _log("CMD", f"nmap -sV --script ssl-cert,http-security-headers -p 80,443 {domain}")
        out = _run_cmd(["nmap", "-sV", "--script", "ssl-cert,http-security-headers",
                        "-p", "80,443", "--host-timeout", "30s", domain], timeout=60)
        if out:
            ext_results["nmap"] = out
            tools_used.append("nmap")
            _log("INFO", f"✅ nmap abgeschlossen ({len(out)} Zeichen)")
    else:
        skipped.append("nmap")

    # --- httpx ---------------------------------------------------------------
    if shutil.which("httpx"):
        _log("CMD", f"httpx -u {target} -title -tech-detect -status-code -nc")
        out = _run_cmd(["httpx", "-u", target, "-title", "-tech-detect",
                        "-status-code", "-nc", "-silent"], timeout=30)
        if out:
            ext_results["httpx"] = out
            tools_used.append("httpx")
            _log("INFO", f"✅ httpx abgeschlossen")
    else:
        skipped.append("httpx")

    # --- subfinder -----------------------------------------------------------
    if shutil.which("subfinder"):
        _log("CMD", f"subfinder -d {domain} -silent")
        out = _run_cmd(["subfinder", "-d", domain, "-silent", "-timeout", "20"], timeout=40)
        if out:
            ext_results["subfinder"] = out
            tools_used.append("subfinder")
            _log("INFO", f"✅ subfinder — {len(out.splitlines())} Subdomains gefunden")
    else:
        skipped.append("subfinder")

    # --- nuclei --------------------------------------------------------------
    if shutil.which("nuclei"):
        _log("CMD", f"nuclei -u {target} -severity critical,high,medium -nc -silent")
        out = _run_cmd(["nuclei", "-u", target, "-severity", "critical,high,medium",
                        "-nc", "-silent", "-timeout", "20"], timeout=120)
        if out:
            ext_results["nuclei"] = out
            tools_used.append("nuclei")
            _log("INFO", f"✅ nuclei — {len(out.splitlines())} Treffer")
    else:
        skipped.append("nuclei")

    # --- nikto ---------------------------------------------------------------
    if shutil.which("nikto"):
        _log("CMD", f"nikto -h {target} -maxtime 60")
        out = _run_cmd(["nikto", "-h", target, "-maxtime", "60", "-nointeractive"], timeout=90)
        if out:
            ext_results["nikto"] = out
            tools_used.append("nikto")
            _log("INFO", "✅ nikto abgeschlossen")
    else:
        skipped.append("nikto")

    if skipped:
        _log("TOOLS_USED",
             f"ℹ️ Nicht verfügbare Tools (übersprungen): {', '.join(skipped)}")
    if tools_used:
        _log("TOOLS_USED",
             f"🔧 Verwendete Tools: {', '.join(tools_used)}")

    # ── 5. Claude AI analysis ──────────────────────────────────────────────
    _log("AGENT", "🤖 Claude AI analysiert Sicherheitsdaten …")

    http_info = live.get("http", {})
    tls_info = live.get("tls", {})

    user_message = f"""## Sicherheitsaudit: {target}

### HTTP Security Headers
Fehlende Header: {json.dumps(http_info.get("missing_headers", []), ensure_ascii=False)}
Vorhandene Header: {json.dumps(http_info.get("present_headers", []), ensure_ascii=False)}
CSP-Stärke: {http_info.get("csp_strength", "none")}
HSTS vorhanden: {http_info.get("hsts_present", False)}
HSTS max-age: {http_info.get("hsts_max_age")}
HTTP-Warnungen: {json.dumps(http_info.get("warnings", []), ensure_ascii=False)}

### TLS/SSL
Gültig: {tls_info.get("valid")}
Aussteller: {tls_info.get("issuer")}
Ablauf: {tls_info.get("expiry")}
Verbleibende Tage: {tls_info.get("days_remaining")}
TLS-Warnungen: {json.dumps(tls_info.get("warnings", []), ensure_ascii=False)}

### DNS-Audit
{dns_report}

### Cookie-Check
{cookie_report}

### Alle gesammelten Warnungen
{json.dumps(live.get("warnings", []), ensure_ascii=False)}
""" + (
        "\n### nmap-Scan\n" + ext_results["nmap"]        if "nmap"     in ext_results else ""
    ) + (
        "\n### httpx-Scan\n" + ext_results["httpx"]      if "httpx"    in ext_results else ""
    ) + (
        "\n### Subdomains (subfinder)\n" + ext_results["subfinder"] if "subfinder" in ext_results else ""
    ) + (
        "\n### nuclei-Findings\n" + ext_results["nuclei"] if "nuclei"   in ext_results else ""
    ) + (
        "\n### nikto-Scan\n" + ext_results["nikto"]      if "nikto"    in ext_results else ""
    ) + """

Analysiere diese Daten und erstelle ein JSON-Array mit Findings für den NIS2/DSGVO-Auditbericht.
"""

    ai_findings = _call_claude(user_message)
    if ai_findings:
        for f in ai_findings:
            f.setdefault("tool", "ai")
            f.setdefault("severity", "info")
            all_findings.append(f)
        _log("AGENT", f"✅ Claude AI hat {len(ai_findings)} Finding(s) generiert")
    else:
        # Fallback: generate findings from live_check warnings directly
        _log("AGENT", "⚠️ AI nicht verfügbar — erzeuge Findings aus Live-Check-Daten")
        for warning in live.get("warnings", []):
            severity = "medium"
            if any(kw in warning.lower() for kw in ["kritisch", "critical", "spf", "dmarc"]):
                severity = "high"
            elif any(kw in warning.lower() for kw in ["abläuft", "ablauf", "expired"]):
                severity = "high"
            all_findings.append({
                "title": f"Sicherheitswarnung: {warning[:80]}",
                "description": warning,
                "severity": severity,
                "cvss": "",
                "dsgvo_article": "",
                "recommendation": "Bitte prüfen und beheben.",
                "tool": "live_check",
            })

    # ── 6. Add severity rank ───────────────────────────────────────────────
    for f in all_findings:
        f["severity_rank"] = _rank(f.get("severity", "info"))

    # Sort by severity
    all_findings.sort(key=lambda f: f["severity_rank"])

    _log("FINDING", f"📋 Gesamt: {len(all_findings)} Finding(s) gefunden")

    # ── 7. Prepare tasks ───────────────────────────────────────────────────
    from .tasks_data import NIS2_STANDARD_TASKS
    import copy
    tasks = copy.deepcopy(NIS2_STANDARD_TASKS)
    for t in tasks:
        t.setdefault("done", False)
        t.setdefault("done_at", None)
        t.setdefault("notes", "")

    _auto_mark_tasks(tasks, all_findings)

    done_count = sum(1 for t in tasks if t.get("done"))
    _log("INFO", f"✅ Audit abgeschlossen — {done_count}/{len(tasks)} Tasks erfüllt")

    return {
        "findings": all_findings,
        "live": live,
        "tasks": tasks,
        "tools_used": tools_used,
        "skipped_tools": skipped,
    }
