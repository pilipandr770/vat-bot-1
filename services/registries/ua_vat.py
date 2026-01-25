"""Adapter for Ukrainian VAT (ПДВ) payers registry."""

from __future__ import annotations

import datetime as _dt
from typing import Dict, Optional

import requests

from .base import BusinessRegistryAdapter


class UkrainianVatAdapter(BusinessRegistryAdapter):
    """Queries the Ukrainian VAT (ПДВ) payers registry via data.gov.ua."""

    country_code = "UA"
    source = "vat_ua"

    # data.gov.ua API endpoints
    base_url = "https://data.gov.ua/api/3/action/datastore_search"
    vat_resource_id = "b7b9e39e-4c6e-4b7a-8b0a-9b0a0b0a0b0a"  # Реєстр платників ПДВ resource ID

    def lookup(
        self,
        company_name: str,
        vat_number: Optional[str] = None,
        registration_number: Optional[str] = None,
    ) -> Dict:
        """Lookup VAT status in Ukrainian registry."""

        # Use EDRPOU for VAT lookup
        edrpou = registration_number or self.strip_country_prefix(vat_number, self.country_code)

        if not edrpou:
            return self._error_response("EDRPOU required for VAT lookup")

        params = {
            "resource_id": self.vat_resource_id,
            "filters": f'{{"edrpou":{edrpou}}}',
            "limit": 1,
        }

        try:
            resp = requests.get(self.base_url, params=params, timeout=self.timeout)
            response_time = int(resp.elapsed.total_seconds() * 1000)

            if resp.status_code == 404:
                return self._not_found_response(response_time)

            resp.raise_for_status()
            payload = resp.json()

            if not payload.get("success"):
                return self._error_response("VAT registry API returned error")

        except requests.exceptions.Timeout:
            return self._error_response("VAT registry service timeout")
        except requests.RequestException as exc:
            return self._error_response(f"VAT registry API error: {exc}")
        except ValueError:
            return self._error_response("Cannot decode VAT registry response")

        records = payload.get("result", {}).get("records", [])

        if not records:
            return self._not_found_response(response_time)

        record = records[0]

        # Parse VAT status
        status_code = record.get("stan", "").lower()
        is_active = "зареєстрований" in status_code or "registered" in status_code

        data = {
            "registry": "Реєстр платників ПДВ",
            "edrpou": record.get("edrpou"),
            "company_name": record.get("name") or company_name,
            "vat_status": record.get("stan", "Невідомий"),
            "registration_date": record.get("date_reg"),
            "deregistration_date": record.get("date_dereg"),
            "source_payload": record,
            "queried_at": _dt.datetime.utcnow().isoformat(),
        }

        return {
            "status": "valid" if is_active else "warning",
            "source": self.source,
            "data": data,
            "last_checked": _dt.datetime.utcnow().isoformat(),
            "confidence": 0.9 if is_active else 0.7,
            "response_time_ms": response_time,
            "error_message": None,
        }

    def _not_found_response(self, response_time: Optional[int] = None) -> Dict:
        return {
            "status": "warning",
            "source": self.source,
            "data": {
                "message": "Компанія не є платником ПДВ",
                "registry": "Реєстр платників ПДВ",
                "vat_status": "Не зареєстрований",
            },
            "last_checked": _dt.datetime.utcnow().isoformat(),
            "confidence": 0.4,
            "response_time_ms": response_time,
            "error_message": "Not a VAT payer",
        }

    def _error_response(self, message: str) -> Dict:
        return {
            "status": "error",
            "source": self.source,
            "data": {
                "message": message,
                "registry": "Реєстр платників ПДВ",
            },
            "last_checked": _dt.datetime.utcnow().isoformat(),
            "confidence": 0.0,
            "response_time_ms": None,
            "error_message": message,
        }