"""Adapter for Ukrainian EDR (Єдиний державний реєстр) business registry."""

from __future__ import annotations

import datetime as _dt
from typing import Dict, Optional

import requests

from .base import BusinessRegistryAdapter


class UkrainianEdrAdapter(BusinessRegistryAdapter):
    """Queries the Ukrainian EDR (Єдиний державний реєстр) open-data API."""

    country_code = "UA"
    source = "registry_ua_edr"

    # data.gov.ua API endpoints
    base_url = "https://data.gov.ua/api/3/action/datastore_search"
    edr_resource_id = "1c7f3815-3259-45e0-bdf1-64dca07ddc10"  # ЄДР resource ID

    def lookup(
        self,
        company_name: str,
        vat_number: Optional[str] = None,
        registration_number: Optional[str] = None,
    ) -> Dict:
        """Lookup company in Ukrainian EDR registry."""

        # Use EDRPOU (registration number) or VAT number for search
        edrpou = registration_number or self.strip_country_prefix(vat_number, self.country_code)

        params = {
            "resource_id": self.edr_resource_id,
            "limit": 1,  # Get only first match
        }

        # Search by EDRPOU if available, otherwise by company name
        if edrpou:
            params["filters"] = f'{{"edrpou":{edrpou}}}'
        elif company_name:
            # For name search, we'll use a simple contains filter
            params["q"] = company_name
        else:
            return self._error_response("No search parameters for EDR lookup")

        try:
            resp = requests.get(self.base_url, params=params, timeout=self.timeout)
            response_time = int(resp.elapsed.total_seconds() * 1000)

            if resp.status_code == 404:
                return self._not_found_response(response_time)

            resp.raise_for_status()
            payload = resp.json()

            if not payload.get("success"):
                return self._error_response("EDR API returned error")

        except requests.exceptions.Timeout:
            return self._error_response("EDR service timeout")
        except requests.RequestException as exc:
            return self._error_response(f"EDR API error: {exc}")
        except ValueError:
            return self._error_response("Cannot decode EDR response")

        records = payload.get("result", {}).get("records", [])

        if not records:
            return self._not_found_response(response_time)

        record = records[0]

        # Parse status - check if company is active
        status_code = record.get("stan", "").lower()
        is_active = "зареєстрований" in status_code or "registered" in status_code

        # Extract KVED codes (business activities)
        kved_codes = []
        for i in range(1, 6):  # Check up to 5 KVED fields
            kved_field = f"kved{i}"
            if record.get(kved_field):
                kved_codes.append(record.get(kved_field))

        data = {
            "registry": "ЄДР (EDR)",
            "edrpou": record.get("edrpou"),
            "company_name": record.get("name") or company_name,
            "status": record.get("stan", "Невідомий"),
            "registration_date": record.get("date"),
            "kved_codes": kved_codes,
            "address": record.get("address"),
            "director": record.get("boss"),  # керівник
            "legal_form": record.get("opf"),  # організаційно-правова форма
            "source_payload": record,
            "queried_at": _dt.datetime.utcnow().isoformat(),
        }

        return {
            "status": "valid" if is_active else "warning",
            "source": self.source,
            "data": data,
            "last_checked": _dt.datetime.utcnow().isoformat(),
            "confidence": 0.8 if is_active else 0.6,
            "response_time_ms": response_time,
            "error_message": None,
        }

    def _not_found_response(self, response_time: Optional[int] = None) -> Dict:
        return {
            "status": "warning",
            "source": self.source,
            "data": {
                "message": "Компанія не знайдена в ЄДР",
                "registry": "ЄДР (EDR)",
            },
            "last_checked": _dt.datetime.utcnow().isoformat(),
            "confidence": 0.2,
            "response_time_ms": response_time,
            "error_message": "Company not found in EDR",
        }

    def _error_response(self, message: str) -> Dict:
        return {
            "status": "error",
            "source": self.source,
            "data": {
                "message": message,
                "registry": "ЄДР (EDR)",
            },
            "last_checked": _dt.datetime.utcnow().isoformat(),
            "confidence": 0.0,
            "response_time_ms": None,
            "error_message": message,
        }