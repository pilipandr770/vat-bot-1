"""Adapter for the German Handelsregister."""

from __future__ import annotations

from typing import Dict, Optional

from services.handelsregister import HandelsregisterService

from .base import BusinessRegistryAdapter


class GermanHandelsregisterAdapter(BusinessRegistryAdapter):
    """Wraps the existing HandelsregisterService with the adapter API."""

    country_code = "DE"
    source = "handelsregister"

    def __init__(self, timeout: int = 20) -> None:
        super().__init__(timeout=timeout)
        self.service = HandelsregisterService()

    def lookup(
        self,
        company_name: str,
        vat_number: Optional[str] = None,
        registration_number: Optional[str] = None,
    ) -> Dict:
        return self.service.check_company(company_name, registration_number=registration_number)
