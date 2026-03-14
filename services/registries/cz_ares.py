"""Adapter for the Czech ARES open business registry."""

from __future__ import annotations

import datetime as _dt
from typing import Dict, Optional

import requests

from .base import BusinessRegistryAdapter


class CzechAresAdapter(BusinessRegistryAdapter):
    """Queries the Czech ARES open-data API."""

    country_code = "CZ"
    source = "registry_cz"

    base_url = "https://ares.gov.cz/ares/api/ekonomicke-subjekty/v1/ekonomicke-subjekty"

    def lookup(
        self,
        company_name: str,
        vat_number: Optional[str] = None,
        registration_number: Optional[str] = None,
    ) -> Dict:
        ico = registration_number or self.strip_country_prefix(vat_number, self.country_code)
        params: Dict[str, str] = {}

        if ico:
            params["ico"] = ico
        if company_name:
            params["obchodniJmeno"] = company_name

        if not params:
            return self._error_response("No search parameters for ARES lookup")

        try:
            resp = requests.get(self.base_url, params=params, timeout=self.timeout)
            response_time = int(resp.elapsed.total_seconds() * 1000)
            if resp.status_code == 404:
                return self._not_found_response(response_time)
            resp.raise_for_status()
            payload = resp.json()
        except requests.exceptions.Timeout:
            return self._error_response("ARES service timeout")
        except requests.RequestException as exc:
            return self._error_response(f"ARES API error: {exc}")
        except ValueError:
            return self._error_response("Cannot decode ARES response")

        items = (
            payload.get("ekonomickeSubjekty")
            or payload.get("items")
            or payload.get("data")
            or []
        )

        if not items:
            return self._not_found_response(response_time)

        candidate = items[0]
        status_code = str(candidate.get("stavKod", "")).lower()
        is_active = status_code in {"akt", "aktivni", "1", "01"}

        data = {
            "registry": "ARES",
            "ico": candidate.get("ico"),
            "company_name": candidate.get("obchodniJmeno") or company_name,
            "legal_form": candidate.get("pravniForma"),
            "address": candidate.get("sidlo"),
            "founded_at": candidate.get("datumVzniku"),
            "status": candidate.get("stavText"),
            "source_payload": candidate,
            "queried_at": _dt.datetime.utcnow().isoformat(),
        }

        return {
            "status": "valid" if is_active else "warning",
            "source": self.source,
            "data": data,
            "last_checked": _dt.datetime.utcnow().isoformat(),
            "confidence": 0.75 if is_active else 0.55,
            "response_time_ms": response_time,
            "error_message": None,
        }

    def _not_found_response(self, response_time: Optional[int] = None) -> Dict:
        return {
            "status": "warning",
            "source": self.source,
            "data": {
                "message": "No matching company in ARES",
                "registry": "ARES",
            },
            "last_checked": _dt.datetime.utcnow().isoformat(),
            "confidence": 0.3,
            "response_time_ms": response_time,
            "error_message": "Company not found",
        }

    def _error_response(self, message: str) -> Dict:
        return {
            "status": "error",
            "source": self.source,
            "data": {
                "registry": "ARES",
            },
            "last_checked": _dt.datetime.utcnow().isoformat(),
            "confidence": 0.0,
            "response_time_ms": None,
            "error_message": message,
        }
