"""Registry manager that routes to country-specific adapters."""

from __future__ import annotations

from typing import Dict, List, Optional

from services.registries import (
    CzechAresAdapter,
    GermanHandelsregisterAdapter,
    PolishWhiteListAdapter,
    UkrainianEdrAdapter,
    UkrainianVatAdapter,
    UkrainianSanctionsAdapter,
)
from services.ua_registry_service import UkrainianRegistryService


class BusinessRegistryManager:
    """Provides a single entrypoint for business registry lookups."""

    def __init__(self) -> None:
        self.adapters: Dict[str, object] = {
            "DE": GermanHandelsregisterAdapter(),
            "CZ": CzechAresAdapter(),
            "PL": PolishWhiteListAdapter(),
            "UA": UkrainianRegistryService(),  # Combined Ukrainian registry service
        }

        self.catalog: List[Dict] = [
            {
                "code": "DE",
                "label": "Німеччина",
                "status": "available",
                "description": "Handelsregister (open API simulation)",
            },
            {
                "code": "CZ",
                "label": "Чехія",
                "status": "available",
                "description": "ARES – öffentlicher Unternehmensregister",
            },
            {
                "code": "PL",
                "label": "Польща",
                "status": "available",
                "description": "Ministerstwo Finansów – Biała Lista podatników VAT",
            },
            {
                "code": "UA",
                "label": "Україна",
                "status": "available",
                "description": "ЄДР – Єдиний державний реєстр юридичних осіб",
            },
            {
                "code": "AT",
                "label": "Австрія",
                "status": "planned",
                "description": "Firmenbuch – kostenpflichtiger Zugriff (geplant)",
            },
            {
                "code": "FR",
                "label": "Франція",
                "status": "planned",
                "description": "INSEE Sirene – OAuth API (Integration geplant)",
            },
            {
                "code": "NL",
                "label": "Нідерланди",
                "status": "planned",
                "description": "KVK Handelsregister – API Key erforderlich (Premium)",
            },
            {
                "code": "ES",
                "label": "Іспанія",
                "status": "planned",
                "description": "Registro Mercantil/BORME – derzeit nur Premium-Daten",
            },
            {
                "code": "IT",
                "label": "Італія",
                "status": "planned",
                "description": "Registro Imprese – kostenpflichtig, Integration vorbereitet",
            },
            {
                "code": "SE",
                "label": "Швеція",
                "status": "planned",
                "description": "Bolagsverket – API mit Gebühr, auf Roadmap",
            },
            {
                "code": "DK",
                "label": "Данія",
                "status": "planned",
                "description": "CVR (Virksomhedsregistret) – API key benötigt (Premium)",
            },
            {
                "code": "FI",
                "label": "Фінляндія",
                "status": "planned",
                "description": "YTJ Business Information System – Zugang geplant",
            },
            {
                "code": "LU",
                "label": "Люксембург",
                "status": "planned",
                "description": "RCSL – kostenpflichtiger Zugang (Enterprise)",
            },
            {
                "code": "BE",
                "label": "Бельгія",
                "status": "planned",
                "description": "KBO/BCE – Paywall, Integration für Pro/Enterprise",  # noqa: E501
            },
        ]

    # ------------------------------------------------------------------
    def lookup(
        self,
        country_code: str,
        company_name: str,
        vat_number: Optional[str] = None,
        registration_number: Optional[str] = None,
    ) -> Optional[Dict]:
        adapter = self.adapters.get(country_code.upper())
        if not adapter:
            return None
        return adapter.lookup(company_name, vat_number=vat_number, registration_number=registration_number)

    def get_catalog_grouped(self) -> Dict[str, List[Dict]]:
        groups: Dict[str, List[Dict]] = {"available": [], "planned": []}
        for entry in self.catalog:
            key = entry["status"] if entry["status"] in groups else "planned"
            groups.setdefault(key, []).append(entry)
        # Ensure deterministic ordering by label
        for entries in groups.values():
            entries.sort(key=lambda item: item["label"])
        return groups

    def get_status(self, country_code: str) -> Optional[str]:
        for entry in self.catalog:
            if entry["code"].upper() == country_code.upper():
                return entry["status"]
        return None
