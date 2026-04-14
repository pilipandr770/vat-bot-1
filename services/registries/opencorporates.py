"""OpenCorporates adapter — cross-border company registry data.

OpenCorporates aggregates official company registry data from 140+ jurisdictions.

Free tier: ~10 requests/day without API key, ~500/day with free key.
Set env var: OPENCORPORATES_API_KEY=... (optional)

Registration: https://opencorporates.com/users/sign_up

Returns: company status, registration number, directors, filing history URL.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Dict, List, Optional

import requests

from .base import BusinessRegistryAdapter

logger = logging.getLogger(__name__)

# Map ISO country codes to OpenCorporates jurisdiction codes
_JURISDICTION_MAP: Dict[str, str] = {
    "DE": "de",
    "AT": "at",
    "CH": "ch",
    "FR": "fr",
    "NL": "nl",
    "BE": "be",
    "PL": "pl",
    "CZ": "cz",
    "GB": "gb",
    "US": "us_de",  # Delaware as default; OpenCorporates has per-state codes
    "UA": "ua",
    "LU": "lu",
    "SK": "sk",
    "HU": "hu",
    "RO": "ro",
    "IT": "it",
    "ES": "es",
}


class OpenCorporatesAdapter(BusinessRegistryAdapter):
    """
    Queries OpenCorporates API for company data across 140+ countries.

    Primary use:
    - Cross-check registration status
    - Retrieve company officers / directors
    - Detect dissolved or inactive companies
    - Cross-border verification (non-DE companies)
    """

    country_code = "*"  # works for any country
    source = "opencorporates"

    _API_BASE = "https://api.opencorporates.com/v0.4"

    def __init__(self, timeout: int = 12) -> None:
        super().__init__(timeout=timeout)
        self._api_key = os.environ.get("OPENCORPORATES_API_KEY", "").strip()
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "VatBot-Verifier/2.0 (+https://vat-verifizierung.de)",
                "Accept": "application/json",
            }
        )

    # ------------------------------------------------------------------
    def lookup(
        self,
        company_name: str,
        vat_number: Optional[str] = None,
        registration_number: Optional[str] = None,
        country_code: Optional[str] = None,
    ) -> Dict:
        t0 = time.time()
        try:
            jurisdiction = _JURISDICTION_MAP.get((country_code or "").upper())

            # If we have a registration number and jurisdiction, try direct lookup first
            company = None
            if registration_number and jurisdiction:
                company = self._fetch_by_number(registration_number, jurisdiction)

            # Fall back to search
            if not company:
                company = self._search(company_name, jurisdiction)

            elapsed = int((time.time() - t0) * 1000)

            if not company:
                return {
                    "status": "warning",
                    "source": self.source,
                    "data": {
                        "company_name": company_name,
                        "found": False,
                        "message": "Kein Eintrag in OpenCorporates gefunden.",
                    },
                    "confidence": 0.2,
                    "response_time_ms": elapsed,
                    "error_message": None,
                }

            summary = self._build_summary(company)
            status = self._derive_status(company)

            return {
                "status": status,
                "source": self.source,
                "data": {
                    "company_name": company_name,
                    "found": True,
                    "company": company,
                    "summary": summary,
                },
                "confidence": 0.85 if status == "valid" else 0.5,
                "response_time_ms": elapsed,
                "error_message": None,
            }

        except requests.exceptions.HTTPError as exc:
            code = exc.response.status_code if exc.response else 0
            if code == 429:
                return self._error("OpenCorporates: Rate-Limit erreicht. Später erneut versuchen.", t0)
            return self._error(f"OpenCorporates HTTP {code}", t0)
        except requests.exceptions.Timeout:
            return self._error("OpenCorporates: Zeitüberschreitung", t0)
        except Exception as exc:
            logger.warning("OpenCorporatesAdapter error for %s: %s", company_name, exc)
            return self._error(str(exc), t0)

    # ------------------------------------------------------------------
    def _params(self, extra: Optional[Dict] = None) -> Dict:
        """Build request params, injecting API key if available."""
        p: Dict = {}
        if self._api_key:
            p["api_token"] = self._api_key
        if extra:
            p.update(extra)
        return p

    def _fetch_by_number(self, reg_number: str, jurisdiction: str) -> Optional[Dict]:
        """Direct lookup by company_number/jurisdiction."""
        # Strip spaces/dots from number
        num = reg_number.replace(" ", "").replace(".", "")
        url = f"{self._API_BASE}/companies/{jurisdiction}/{num}"
        resp = self._session.get(url, params=self._params(), timeout=self.timeout)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json().get("results", {}).get("company")

    def _search(self, company_name: str, jurisdiction: Optional[str]) -> Optional[Dict]:
        """Search by company name, optionally filtered by jurisdiction."""
        params = self._params({"q": company_name, "per_page": 5})
        if jurisdiction:
            params["jurisdiction_code"] = jurisdiction

        resp = self._session.get(
            f"{self._API_BASE}/companies/search",
            params=params,
            timeout=self.timeout,
        )
        resp.raise_for_status()

        companies = (
            resp.json()
            .get("results", {})
            .get("companies", [])
        )
        if not companies:
            return None

        # Pick the best-matching result (first active, else first)
        active = [c for c in companies if (c.get("company") or {}).get("current_status", "").lower() in ("active", "aktiv", "")]
        candidates = active or companies
        return candidates[0].get("company") if candidates else None

    def _build_summary(self, c: Dict) -> Dict:
        officers = c.get("officers") or []
        directors = [
            o.get("officer", o).get("name", "")
            for o in officers[:5]
            if isinstance(o, dict)
        ]

        return {
            "company_number": c.get("company_number"),
            "jurisdiction": c.get("jurisdiction_code"),
            "status": c.get("current_status"),
            "incorporation_date": c.get("incorporation_date"),
            "dissolution_date": c.get("dissolution_date"),
            "registered_address": (c.get("registered_address") or {}).get("in_full"),
            "company_type": c.get("company_type"),
            "directors": [d for d in directors if d],
            "opencorporates_url": c.get("opencorporates_url"),
            "source_url": c.get("source_url"),
        }

    def _derive_status(self, c: Dict) -> str:
        status_str = (c.get("current_status") or "").lower()
        if c.get("dissolution_date") or any(
            word in status_str for word in ("dissolv", "liquidat", "struck off", "inactive", "insolvent")
        ):
            return "error"
        if status_str in ("active", "aktiv", "registered") or not status_str:
            return "valid"
        return "warning"

    def _error(self, msg: str, t0: float) -> Dict:
        return {
            "status": "warning",
            "source": self.source,
            "data": {"error": msg},
            "confidence": 0.0,
            "response_time_ms": int((time.time() - t0) * 1000),
            "error_message": msg,
        }
