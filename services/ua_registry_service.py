"""Ukrainian business registry services combining multiple data sources."""

from __future__ import annotations

import datetime as _dt
from typing import Dict, Optional

from services.registries.ua_edr import UkrainianEdrAdapter
from services.registries.ua_vat import UkrainianVatAdapter
from services.registries.ua_sanctions import UkrainianSanctionsAdapter


class UkrainianRegistryService:
    """Combines Ukrainian business registry checks: EDR, VAT, Sanctions."""

    def __init__(self):
        self.edr_adapter = UkrainianEdrAdapter()
        self.vat_adapter = UkrainianVatAdapter()
        self.sanctions_adapter = UkrainianSanctionsAdapter()

    def check_company(
        self,
        company_name: str,
        registration_number: Optional[str] = None,
        vat_number: Optional[str] = None,
    ) -> Dict:
        """
        Comprehensive Ukrainian company check combining multiple registries.

        Returns standardized response with company data and risk assessment.
        """

        # Primary check: EDR (company registry)
        edr_result = self.edr_adapter.lookup(
            company_name=company_name,
            registration_number=registration_number,
            vat_number=vat_number
        )

        # VAT status check
        vat_result = self.vat_adapter.lookup(
            company_name=company_name,
            registration_number=registration_number,
            vat_number=vat_number
        )

        # Sanctions check
        sanctions_result = self.sanctions_adapter.lookup(
            company_name=company_name,
            registration_number=registration_number,
            vat_number=vat_number
        )

        # Combine results
        combined_data = {
            "company_name": company_name,
            "edrpou": registration_number,
            "country": "Ukraine",
            "registry_checks": {
                "edr": edr_result,
                "vat": vat_result,
                "sanctions": sanctions_result,
            },
            "queried_at": _dt.datetime.utcnow().isoformat(),
        }

        # Determine overall status based on checks
        overall_status = "valid"
        risk_flags = []
        confidence = 0.8

        # Sanctions hit is critical
        if sanctions_result.get("status") == "error":
            overall_status = "error"
            risk_flags.append("sanctions_hit")
            confidence = 0.95

        # Company not found in EDR
        elif edr_result.get("status") in ["warning", "error"]:
            overall_status = "warning"
            risk_flags.append("not_registered")
            confidence = 0.4

        # VAT status
        if vat_result.get("status") == "valid":
            combined_data["vat_registered"] = True
        else:
            combined_data["vat_registered"] = False
            risk_flags.append("no_vat_registration")

        # Add company data from EDR if available
        if edr_result.get("status") == "valid" and edr_result.get("data"):
            edr_data = edr_result["data"]
            combined_data.update({
                "registration_date": edr_data.get("registration_date"),
                "legal_form": edr_data.get("legal_form"),
                "status": edr_data.get("status"),
                "address": edr_data.get("address"),
                "director": edr_data.get("director"),
                "kved_codes": edr_data.get("kved_codes", []),
            })

        combined_data["risk_flags"] = risk_flags

        return {
            "status": overall_status,
            "source": "registry_ua_combined",
            "data": combined_data,
            "last_checked": _dt.datetime.utcnow().isoformat(),
            "confidence": confidence,
            "response_time_ms": None,  # Combined timing would be complex
            "error_message": None,
        }