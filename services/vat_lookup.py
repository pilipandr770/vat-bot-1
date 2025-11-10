"""Service for automatic VAT-based data enrichment."""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from services.vies import VIESService
from services.business_registry import BusinessRegistryManager


class VatLookupService:
    """Aggregates VIES and registry lookups to prefill counterparty data."""

    def __init__(self) -> None:
        self.vies_service = VIESService()
        self.registry_manager = BusinessRegistryManager()

    def lookup(
        self,
        vat_number: str,
        country_code: Optional[str] = None,
        company_name_hint: Optional[str] = None,
    ) -> Dict:
        vat_number_clean = (vat_number or "").strip().replace(" ", "")
        if not vat_number_clean:
            raise ValueError("VAT-Nummer fehlt")

        vat_number_clean = vat_number_clean.upper()

        derived_country = vat_number_clean[:2] if len(vat_number_clean) >= 2 else ""
        if country_code:
            country_code = country_code.upper()
        elif re.match(r"^[A-Z]{2}$", derived_country):
            country_code = derived_country
        else:
            raise ValueError("Konnte Länderkennzeichen der VAT-Nummer nicht ermitteln")

        format_info = self.vies_service.validate_vat_format(country_code, vat_number_clean)

        vies_result = self.vies_service.validate_vat(country_code, vat_number_clean)
        services: Dict[str, Dict] = {"vies": vies_result}
        messages: List[Dict[str, str]] = []

        prefills: Dict[str, Optional[str]] = {}
        prefills["counterparty_vat"] = f"{country_code}{self.vies_service._clean_vat_number(vat_number_clean, country_code)}"
        prefills["counterparty_country"] = country_code

        if not format_info.get("valid") and format_info.get("pattern"):
            messages.append({
                "level": "warning",
                "text": format_info.get("message", "Unbekannter VAT-Formatstatus"),
            })

        if vies_result.get("status") != "valid":
            error_msg = vies_result.get("error_message") or "VAT konnte nicht validiert werden"
            messages.append({"level": "danger", "text": error_msg})
            return {
                "success": False,
                "prefill": prefills,
                "messages": messages,
                "services": services,
                "country_code": country_code,
                "registry_status": self.registry_manager.get_status(country_code),
            }

        vies_data = vies_result.get("data", {})
        company_name = vies_data.get("company_name") or company_name_hint
        if company_name:
            prefills["counterparty_name"] = company_name
        if vies_data.get("company_address"):
            prefills["counterparty_address"] = vies_data["company_address"]
        if vies_data.get("country_code"):
            prefills["counterparty_country"] = vies_data["country_code"]

        messages.append({
            "level": "success",
            "text": "Firmendaten wurden über VIES geladen",
        })

        registry_status = self.registry_manager.get_status(country_code)
        registry_result = None

        if registry_status == "available" and company_name:
            registry_result = self.registry_manager.lookup(
                country_code,
                company_name,
                vat_number=self.vies_service._clean_vat_number(vat_number_clean, country_code),
            )
            if registry_result:
                services[registry_result.get("source", f"registry_{country_code.lower()}")] = registry_result
                reg_data = registry_result.get("data", {})
                if not prefills.get("counterparty_name") and reg_data.get("company_name"):
                    prefills["counterparty_name"] = reg_data.get("company_name")
                if reg_data.get("address") and not prefills.get("counterparty_address"):
                    address_value = reg_data.get("address")
                    prefills["counterparty_address"] = (
                        address_value if isinstance(address_value, str) else str(address_value)
                    )
                reg_status = registry_result.get("status")
                if reg_status == "valid":
                    messages.append({
                        "level": "info",
                        "text": f"Handelsregisterdaten ({country_code}) wurden ergänzt",
                    })
                elif reg_status == "warning":
                    messages.append({
                        "level": "warning",
                        "text": registry_result.get("error_message")
                        or f"Keine eindeutigen Handelsregisterdaten für {country_code} gefunden",
                    })
                elif reg_status == "error":
                    messages.append({
                        "level": "danger",
                        "text": registry_result.get("error_message")
                        or f"Fehler beim Handelsregisterabruf für {country_code}",
                    })

        if registry_status and registry_status != "available":
            messages.append({
                "level": "info",
                "text": f"Erweiterte Registerdaten für {country_code} sind in Vorbereitung/Premium",
            })

        return {
            "success": True,
            "prefill": prefills,
            "messages": messages,
            "services": services,
            "country_code": prefills.get("counterparty_country", country_code),
            "registry_status": registry_status,
            "format": format_info,
        }
