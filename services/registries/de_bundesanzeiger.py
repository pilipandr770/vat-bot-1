"""Adapter for Bundesanzeiger.de — mandatory German company publications.

Bundesanzeiger requires all German companies to publish:
- Annual financial statements (Jahresabschluss) — most important
- Major corporate events (mergers, dissolution, capital changes)
- Insolvency proceedings (Insolvenzbekanntmachungen)

No API key required. Uses the public JSON search endpoint.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

from .base import BusinessRegistryAdapter

logger = logging.getLogger(__name__)

# Publication categories (category codes used in Bundesanzeiger)
_CATEGORY_LABELS = {
    "JAHRESABSCHLUSS": "Jahresabschluss",
    "LAGEBERICHT": "Lagebericht",
    "INSOLVENZ": "Insolvenzbekanntmachung",
    "GESELLSCHAFTER": "Gesellschafterliste",
    "BEKANNTMACHUNG": "Bekanntmachung",
    "RECHNUNGSLEGUNG": "Rechnungslegung",
}

# If a company hasn't filed in this many years → warning
_FILING_GAP_WARN_YEARS = 2


class BundesanzeigerAdapter(BusinessRegistryAdapter):
    """
    Searches Bundesanzeiger.de for mandatory company publications.

    Valuable signals for due diligence:
    - Has the company filed a recent Jahresabschluss?  (missing = high risk)
    - Any insolvency proceedings published?            (present = block)
    - Filing frequency trend                           (irregular = warning)
    """

    country_code = "DE"
    source = "bundesanzeiger"

    # Public JSON endpoint used by the Bundesanzeiger search frontend
    SEARCH_URL = "https://www.bundesanzeiger.de/pub/de/resultJson"

    def __init__(self, timeout: int = 15) -> None:
        super().__init__(timeout=timeout)
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (compatible; VatBot-Verifier/2.0; "
                    "+https://vat-verifizierung.de)"
                ),
                "Accept": "application/json, */*",
                "Referer": "https://www.bundesanzeiger.de/pub/de/search",
            }
        )

    # ------------------------------------------------------------------
    def lookup(
        self,
        company_name: str,
        vat_number: Optional[str] = None,
        registration_number: Optional[str] = None,
    ) -> Dict:
        t0 = time.time()
        try:
            publications = self._fetch_publications(company_name)
            elapsed = int((time.time() - t0) * 1000)

            if not publications:
                return {
                    "status": "warning",
                    "source": self.source,
                    "data": {
                        "company_name": company_name,
                        "publications": [],
                        "summary": {
                            "total": 0,
                            "annual_reports": 0,
                            "insolvency_notices": 0,
                            "last_filing_date": None,
                            "last_annual_report_date": None,
                            "has_insolvency": False,
                            "filing_gap_years": None,
                            "interpretation": "Keine Publikationen gefunden — kein Pflichtveröffentlichungspflichtige Gesellschaft oder Daten fehlen.",
                        },
                    },
                    "confidence": 0.3,
                    "response_time_ms": elapsed,
                    "error_message": None,
                }

            summary = self._build_summary(publications, company_name)
            status = self._derive_status(summary)

            return {
                "status": status,
                "source": self.source,
                "data": {
                    "company_name": company_name,
                    "publications": publications[:20],  # cap at 20 for storage
                    "summary": summary,
                },
                "confidence": 0.85 if status == "valid" else 0.6,
                "response_time_ms": elapsed,
                "error_message": None,
            }

        except requests.exceptions.Timeout:
            return self._error("Bundesanzeiger-Anfrage Zeitüberschreitung", t0)
        except Exception as exc:
            logger.warning("BundesanzeigerAdapter error for %s: %s", company_name, exc)
            return self._error(str(exc), t0)

    # ------------------------------------------------------------------
    def _fetch_publications(self, company_name: str) -> List[Dict]:
        """Query the Bundesanzeiger JSON endpoint."""
        params = {
            "query": company_name,
            "category": "",
            "dateFrom": "",
            "dateTo": "",
        }
        resp = self._session.get(self.SEARCH_URL, params=params, timeout=self.timeout)
        resp.raise_for_status()

        raw = resp.json()

        # The API may return a list directly or nested under a key
        hits = []
        if isinstance(raw, list):
            hits = raw
        elif isinstance(raw, dict):
            hits = raw.get("hits") or raw.get("results") or raw.get("content") or []

        results = []
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            entry = {
                "date": self._parse_date(
                    hit.get("publication_date") or hit.get("date") or hit.get("datum") or ""
                ),
                "category": self._normalize_category(
                    hit.get("category") or hit.get("kategorie") or hit.get("publicationCategory") or ""
                ),
                "title": (hit.get("subject") or hit.get("title") or hit.get("betreff") or "")[:200],
                "company": (hit.get("company_name") or hit.get("firma") or "")[:150],
                "court": (hit.get("court") or hit.get("gericht") or "")[:100],
                "url": hit.get("url") or hit.get("link") or None,
            }
            results.append(entry)

        # Sort newest-first
        results.sort(key=lambda x: x["date"] or "", reverse=True)
        return results

    def _parse_date(self, raw: str) -> Optional[str]:
        """Normalize date string to ISO format (YYYY-MM-DD)."""
        if not raw:
            return None
        raw = raw.strip()
        for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
            try:
                return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        # Try regex for partial formats
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)
        if m:
            return m.group(0)
        return raw[:10] if len(raw) >= 10 else raw

    def _normalize_category(self, raw: str) -> str:
        raw_up = raw.upper().replace("-", "").replace(" ", "")
        for key, label in _CATEGORY_LABELS.items():
            if key in raw_up:
                return label
        return raw.strip()[:80] if raw else "Sonstige"

    def _build_summary(self, publications: List[Dict], company_name: str) -> Dict:
        annual = [p for p in publications if "Jahresabschluss" in (p.get("category") or "")]
        insolvency = [
            p for p in publications
            if "Insolvenz" in (p.get("category") or "") or "insolvenz" in (p.get("title") or "").lower()
        ]

        last_date = publications[0]["date"] if publications else None
        last_annual = annual[0]["date"] if annual else None

        # Calculate filing gap
        gap_years = None
        if last_annual:
            try:
                last_dt = datetime.strptime(last_annual, "%Y-%m-%d")
                gap_years = round((datetime.utcnow() - last_dt).days / 365, 1)
            except ValueError:
                pass

        # Interpretation text
        if insolvency:
            interpretation = (
                f"⚠️ Insolvenzbekanntmachung gefunden ({len(insolvency)} Einträge). "
                "Dringend prüfen!"
            )
        elif gap_years is not None and gap_years > _FILING_GAP_WARN_YEARS:
            interpretation = (
                f"Letzter Jahresabschluss: vor {gap_years:.0f} Jahren. "
                "Unregelmäßige Pflichtveröffentlichung — erhöhtes Risiko."
            )
        elif last_annual:
            interpretation = (
                f"Regelmäßige Veröffentlichungen. Letzter Jahresabschluss: {last_annual}."
            )
        else:
            interpretation = (
                "Publikationen gefunden, jedoch kein Jahresabschluss identifiziert. "
                "Möglicherweise nicht bilanzierungspflichtig."
            )

        return {
            "total": len(publications),
            "annual_reports": len(annual),
            "insolvency_notices": len(insolvency),
            "last_filing_date": last_date,
            "last_annual_report_date": last_annual,
            "has_insolvency": len(insolvency) > 0,
            "filing_gap_years": gap_years,
            "recent_categories": list({p["category"] for p in publications[:10]}),
            "interpretation": interpretation,
        }

    def _derive_status(self, summary: Dict) -> str:
        if summary["has_insolvency"]:
            return "error"
        gap = summary.get("filing_gap_years")
        if gap is not None and gap > _FILING_GAP_WARN_YEARS:
            return "warning"
        if summary["total"] == 0:
            return "warning"
        return "valid"

    def _error(self, msg: str, t0: float) -> Dict:
        return {
            "status": "warning",  # degraded, not blocking
            "source": self.source,
            "data": {"error": msg},
            "confidence": 0.0,
            "response_time_ms": int((time.time() - t0) * 1000),
            "error_message": msg,
        }
