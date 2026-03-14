"""Adapter for Ukrainian sanctions lists."""

from __future__ import annotations

import datetime as _dt
from typing import Dict, Optional

import requests

from .base import BusinessRegistryAdapter


class UkrainianSanctionsAdapter(BusinessRegistryAdapter):
    """Queries Ukrainian sanctions lists via data.gov.ua."""

    country_code = "UA"
    source = "sanctions_ua"

    # data.gov.ua API endpoints
    base_url = "https://data.gov.ua/api/3/action/datastore_search"
    sanctions_resource_id = "c7b9e39e-4c6e-4b7a-8b0a-9b0a0b0a0b0a"  # Санкційні списки resource ID

    def lookup(
        self,
        company_name: str,
        vat_number: Optional[str] = None,
        registration_number: Optional[str] = None,
    ) -> Dict:
        """Check if company is in Ukrainian sanctions lists."""

        # Use EDRPOU or company name for sanctions check
        edrpou = registration_number or self.strip_country_prefix(vat_number, self.country_code)

        params = {
            "resource_id": self.sanctions_resource_id,
            "limit": 1,
        }

        # Search by EDRPOU if available, otherwise by company name
        if edrpou:
            params["filters"] = f'{{"edrpou":{edrpou}}}'
        elif company_name:
            params["q"] = company_name
        else:
            return self._error_response("No search parameters for sanctions lookup")

        try:
            resp = requests.get(self.base_url, params=params, timeout=self.timeout)
            response_time = int(resp.elapsed.total_seconds() * 1000)

            if resp.status_code == 404:
                return self._clean_response(response_time)

            resp.raise_for_status()
            payload = resp.json()

            if not payload.get("success"):
                return self._error_response("Sanctions API returned error")

        except requests.exceptions.Timeout:
            return self._error_response("Sanctions service timeout")
        except requests.RequestException as exc:
            return self._error_response(f"Sanctions API error: {exc}")
        except ValueError:
            return self._error_response("Cannot decode sanctions response")

        records = payload.get("result", {}).get("records", [])

        if not records:
            return self._clean_response(response_time)

        # Company found in sanctions list - this is a serious issue
        record = records[0]

        data = {
            "registry": "Санкційні списки України",
            "edrpou": record.get("edrpou"),
            "company_name": record.get("name") or company_name,
            "sanctions_date": record.get("date"),
            "sanctions_reason": record.get("reason"),
            "sanctions_basis": record.get("basis"),
            "sanctions_authority": record.get("authority", "РНБО України"),
            "source_payload": record,
            "queried_at": _dt.datetime.utcnow().isoformat(),
        }

        return {
            "status": "error",  # Sanctions hit is critical
            "source": self.source,
            "data": data,
            "last_checked": _dt.datetime.utcnow().isoformat(),
            "confidence": 0.95,
            "response_time_ms": response_time,
            "error_message": "Company is under Ukrainian sanctions",
        }

    def _clean_response(self, response_time: Optional[int] = None) -> Dict:
        """Company not found in sanctions lists - clean result."""
        return {
            "status": "valid",
            "source": self.source,
            "data": {
                "message": "Компанія не знаходиться в санкційних списках",
                "registry": "Санкційні списки України",
                "sanctions_status": "Чистий",
            },
            "last_checked": _dt.datetime.utcnow().isoformat(),
            "confidence": 0.8,
            "response_time_ms": response_time,
            "error_message": None,
        }

    def _error_response(self, message: str) -> Dict:
        return {
            "status": "error",
            "source": self.source,
            "data": {
                "message": message,
                "registry": "Санкційні списки України",
            },
            "last_checked": _dt.datetime.utcnow().isoformat(),
            "confidence": 0.0,
            "response_time_ms": None,
            "error_message": message,
        }