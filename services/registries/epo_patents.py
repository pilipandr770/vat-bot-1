"""EPO OPS (Open Patent Services) adapter — patent portfolio analysis.

Queries the European Patent Office public API to retrieve patent applications
for a given company. Helps assess whether a company is a genuine innovator
or a shell entity.

Setup (free registration required):
  https://developers.epo.org/ → register → Consumer Key + Secret
  Set env vars:
    EPO_OPS_CONSUMER_KEY=...
    EPO_OPS_CONSUMER_SECRET=...

If the env vars are not set, the adapter returns an empty result and does
NOT block the verification — it is purely additive.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Dict, List, Optional
from urllib.parse import quote

import requests

from .base import BusinessRegistryAdapter

logger = logging.getLogger(__name__)

# IPC main-group → human-readable technology area
_IPC_AREAS: Dict[str, str] = {
    "A": "Alltägliche Bedarfsgüter",
    "B": "Verfahrenstechnik / Transport",
    "C": "Chemie / Metallurgie",
    "D": "Textilien / Papier",
    "E": "Bauwesen",
    "F": "Maschinenbau / Beleuchtung / Heizung",
    "G": "Physik / Elektronik",
    "H": "Elektrotechnik",
}


class EpoPatentsAdapter(BusinessRegistryAdapter):
    """
    Retrieves patent portfolio summary for a company via EPO OPS.

    Returns:
    - Total patent count & active patents
    - Technology areas (IPC sections)
    - Filing trend (is the company still filing?)
    - Most recent application date
    """

    country_code = "*"  # global — not country-specific
    source = "epo_patents"

    _AUTH_URL = "https://ops.epo.org/3.2/auth/accesstoken"
    _SEARCH_URL = "https://ops.epo.org/3.2/rest-services/published-data/search"

    def __init__(self, timeout: int = 12) -> None:
        super().__init__(timeout=timeout)
        self._consumer_key = os.environ.get("EPO_OPS_CONSUMER_KEY", "").strip()
        self._consumer_secret = os.environ.get("EPO_OPS_CONSUMER_SECRET", "").strip()
        self._access_token: Optional[str] = None
        self._token_expires: float = 0.0
        self._session = requests.Session()

    # ------------------------------------------------------------------
    @property
    def _is_configured(self) -> bool:
        return bool(self._consumer_key and self._consumer_secret)

    def lookup(
        self,
        company_name: str,
        vat_number: Optional[str] = None,
        registration_number: Optional[str] = None,
    ) -> Dict:
        t0 = time.time()

        if not self._is_configured:
            return self._not_configured(company_name, t0)

        try:
            token = self._get_token()
            patents = self._search_patents(company_name, token)
            elapsed = int((time.time() - t0) * 1000)
            summary = self._build_summary(patents, company_name)

            return {
                "status": "valid" if patents else "warning",
                "source": self.source,
                "data": {
                    "company_name": company_name,
                    "patents": patents[:15],  # recent 15
                    "summary": summary,
                },
                "confidence": 0.9 if patents else 0.4,
                "response_time_ms": elapsed,
                "error_message": None,
            }

        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code in (401, 403):
                logger.warning("EPO OPS: authentication failed — check credentials")
                return self._error("EPO OPS: Authentifizierung fehlgeschlagen. Credentials prüfen.", t0)
            return self._error(f"EPO HTTP {exc.response.status_code if exc.response else '?'}", t0)
        except requests.exceptions.Timeout:
            return self._error("EPO OPS: Zeitüberschreitung", t0)
        except Exception as exc:
            logger.warning("EpoPatentsAdapter error for %s: %s", company_name, exc)
            return self._error(str(exc), t0)

    # ------------------------------------------------------------------
    def _get_token(self) -> str:
        """Return a cached or freshly-obtained OAuth2 access token."""
        if self._access_token and time.time() < self._token_expires - 30:
            return self._access_token

        resp = self._session.post(
            self._AUTH_URL,
            data={"grant_type": "client_credentials"},
            auth=(self._consumer_key, self._consumer_secret),
            timeout=10,
        )
        resp.raise_for_status()
        payload = resp.json()
        self._access_token = payload["access_token"]
        self._token_expires = time.time() + int(payload.get("expires_in", 3600))
        return self._access_token

    def _search_patents(self, company_name: str, token: str) -> List[Dict]:
        """Search EPO OPS for patents by applicant name."""
        # CQL query: pa = "Applicant Name"
        query = f'pa="{company_name}"'
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "X-OPS-Range": "1-25",
        }
        params = {"q": query, "Range": "1-25"}
        resp = self._session.get(
            f"{self._SEARCH_URL}/biblio",
            params=params,
            headers=headers,
            timeout=self.timeout,
        )
        resp.raise_for_status()

        return self._parse_biblio(resp.json(), company_name)

    def _parse_biblio(self, raw: Dict, company_name: str) -> List[Dict]:
        """Parse OPS biblio response into a flat list."""
        patents = []
        try:
            results = (
                raw.get("ops:world-patent-data", {})
                .get("ops:biblio-search", {})
                .get("ops:search-result", {})
                .get("exchange-documents", [])
            )
            if isinstance(results, dict):
                results = [results]

            for doc in results:
                exch = doc.get("exchange-document", doc)
                if isinstance(exch, list):
                    exch = exch[0]

                bib = exch.get("bibliographic-data", {})
                pub_ref = bib.get("publication-reference", {}) or {}
                doc_id = (
                    pub_ref.get("document-id", [{}])
                    if isinstance(pub_ref.get("document-id"), list)
                    else [pub_ref.get("document-id", {})]
                )
                doc_id = doc_id[0] if doc_id else {}

                # Title
                title_raw = bib.get("invention-title", "")
                if isinstance(title_raw, list):
                    title = next(
                        (t.get("$", t) if isinstance(t, dict) else str(t)
                         for t in title_raw if (t.get("@lang") == "en" if isinstance(t, dict) else True)),
                        "",
                    )
                elif isinstance(title_raw, dict):
                    title = title_raw.get("$", "")
                else:
                    title = str(title_raw or "")

                # IPC
                ipc_raw = bib.get("classifications-ipcr", {})
                ipc_list = ipc_raw.get("classification-ipcr", []) if isinstance(ipc_raw, dict) else []
                if isinstance(ipc_list, dict):
                    ipc_list = [ipc_list]
                ipc_codes = []
                for ipc in ipc_list:
                    if isinstance(ipc, dict):
                        section = ipc.get("section", {})
                        code = section.get("$", "") if isinstance(section, dict) else str(section)
                        if code:
                            ipc_codes.append(code.strip())

                # Date
                date_raw = doc_id.get("date", {})
                date_str = date_raw.get("$", "") if isinstance(date_raw, dict) else str(date_raw or "")

                patents.append({
                    "application_number": str(doc_id.get("doc-number", {}).get("$", "") if isinstance(doc_id.get("doc-number"), dict) else doc_id.get("doc-number", "")),
                    "title": title[:200],
                    "date": date_str[:10] if date_str else None,
                    "ipc_codes": ipc_codes[:5],
                    "technology_areas": list({
                        _IPC_AREAS.get(c[0], "Sonstige") for c in ipc_codes if c
                    }),
                })
        except (KeyError, TypeError, IndexError) as exc:
            logger.debug("EPO parse error: %s", exc)
        return patents

    def _build_summary(self, patents: List[Dict], company_name: str) -> Dict:
        if not patents:
            return {
                "total_found": 0,
                "technology_areas": [],
                "most_recent_date": None,
                "filing_active": False,
                "interpretation": "Keine Patente auf EPO-Datenbank gefunden.",
            }

        # Technology area distribution
        area_counts: Dict[str, int] = {}
        for p in patents:
            for area in p.get("technology_areas") or []:
                area_counts[area] = area_counts.get(area, 0) + 1
        top_areas = sorted(area_counts, key=lambda k: -area_counts[k])[:5]

        # Most recent filing
        dates = [p["date"] for p in patents if p.get("date")]
        most_recent = max(dates) if dates else None

        # Is company still actively filing? (filed within last 3 years)
        filing_active = False
        if most_recent:
            try:
                from datetime import datetime
                yr = int(most_recent[:4])
                filing_active = (datetime.utcnow().year - yr) <= 3
            except (ValueError, TypeError):
                pass

        return {
            "total_found": len(patents),
            "technology_areas": top_areas,
            "most_recent_date": most_recent,
            "filing_active": filing_active,
            "interpretation": (
                f"{len(patents)} Patente gefunden. "
                f"Technologiebereiche: {', '.join(top_areas) or 'k.A.'}. "
                + ("Aktive Anmeldungen in den letzten 3 Jahren." if filing_active
                   else "Keine aktuellen Anmeldungen.")
            ),
        }

    def _not_configured(self, company_name: str, t0: float) -> Dict:
        return {
            "status": "warning",
            "source": self.source,
            "data": {
                "company_name": company_name,
                "summary": {
                    "total_found": 0,
                    "technology_areas": [],
                    "most_recent_date": None,
                    "filing_active": False,
                    "interpretation": (
                        "EPO OPS API nicht konfiguriert. "
                        "Setzen Sie EPO_OPS_CONSUMER_KEY und EPO_OPS_CONSUMER_SECRET "
                        "für Patentdaten."
                    ),
                },
            },
            "confidence": 0.0,
            "response_time_ms": int((time.time() - t0) * 1000),
            "error_message": "EPO OPS not configured",
        }

    def _error(self, msg: str, t0: float) -> Dict:
        return {
            "status": "warning",
            "source": self.source,
            "data": {"error": msg},
            "confidence": 0.0,
            "response_time_ms": int((time.time() - t0) * 1000),
            "error_message": msg,
        }
