"""Adapter for the Polish Ministry of Finance VAT White List."""

from __future__ import annotations

import datetime as _dt
from typing import Dict, Optional

import requests

from .base import BusinessRegistryAdapter


class PolishWhiteListAdapter(BusinessRegistryAdapter):
    """Uses the public White List API (Ministerstwo Finansów)."""

    country_code = "PL"
    source = "registry_pl"

    base_url = "https://wl-api.mf.gov.pl/api/search/nip/{nip}"

    def lookup(
        self,
        company_name: str,
        vat_number: Optional[str] = None,
        registration_number: Optional[str] = None,
    ) -> Dict:
        nip = registration_number or self.strip_country_prefix(vat_number, self.country_code)
        if not nip:
            return self._error_response("Polish VAT number (NIP) required for lookup")

        date_str = _dt.date.today().isoformat()
        url = self.base_url.format(nip=nip)
        params = {"date": date_str}

        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
            response_time = int(resp.elapsed.total_seconds() * 1000)
            if resp.status_code == 404:
                return self._not_found_response(response_time)
            resp.raise_for_status()
            payload = resp.json()
        except requests.exceptions.Timeout:
            return self._error_response("White List service timeout")
        except requests.RequestException as exc:
            return self._error_response(f"White List API error: {exc}")
        except ValueError:
            return self._error_response("Cannot decode White List response")

        result = (payload.get("result") or {}).get("subject")
        if not result:
            return self._not_found_response(response_time)

        status_vat = (result.get("statusVat") or "").lower()
        is_active = status_vat in {"czynny", "active"}

        data = {
            "registry": "Polish MF White List",
            "nip": result.get("nip"),
            "regon": result.get("regon"),
            "company_name": result.get("name") or company_name,
            "status_vat": result.get("statusVat"),
            "account_numbers": result.get("accountNumbers"),
            "representatives": result.get("representatives"),
            "authorized_clerks": result.get("authorizedClerks"),
            "partners": result.get("partners"),
            "source_payload": result,
            "queried_at": _dt.datetime.utcnow().isoformat(),
        }

        return {
            "status": "valid" if is_active else "warning",
            "source": self.source,
            "data": data,
            "last_checked": _dt.datetime.utcnow().isoformat(),
            "confidence": 0.85 if is_active else 0.6,
            "response_time_ms": response_time,
            "error_message": None,
        }

    def _not_found_response(self, response_time: Optional[int] = None) -> Dict:
        return {
            "status": "warning",
            "source": self.source,
            "data": {
                "message": "No matching company in White List",
                "registry": "Polish MF White List",
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
                "registry": "Polish MF White List",
            },
            "last_checked": _dt.datetime.utcnow().isoformat(),
            "confidence": 0.0,
            "response_time_ms": None,
            "error_message": message,
        }
