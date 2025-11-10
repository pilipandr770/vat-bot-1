"""Base classes and utilities for business registry adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Optional


class BusinessRegistryAdapter(ABC):
    """Abstract adapter for querying country-specific business registries."""

    country_code: str
    source: str

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout

    @abstractmethod
    def lookup(
        self,
        company_name: str,
        vat_number: Optional[str] = None,
        registration_number: Optional[str] = None,
    ) -> Dict:
        """Run a registry lookup and return a standardized response dict."""

    # Helper ---------------------------------------------------------------
    @staticmethod
    def strip_country_prefix(value: Optional[str], country_code: str) -> Optional[str]:
        """Remove the ISO country prefix from VAT numbers when present."""
        if not value:
            return value
        value = value.strip()
        if value.upper().startswith(country_code.upper()):
            return value[len(country_code) :]
        return value
