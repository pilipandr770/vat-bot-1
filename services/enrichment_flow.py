# FILE: services/enrichment_flow.py

from __future__ import annotations
from typing import Optional, Dict, Any

from services.vat_lookup import VatLookupService
from services.business_registry import BusinessRegistryManager
from services.osint.scanner import OsintScanner


class EnrichmentOrchestrator:
    """
    Single entry point for counterparty data enrichment.
    Works with free sources:
    - VIES
    - Business registries (DE/CZ/PL)
    - OSINT by domain/email (Whois, DNS, SSL, headers, social networks)
    """

    def __init__(self) -> None:
        self.vat_lookup = VatLookupService()
        self.registry_manager = BusinessRegistryManager()

    # ------------------ ПУБЛІЧНИЙ МЕТОД ------------------
    def enrich(
        self,
        vat_number: Optional[str] = None,
        domain: Optional[str] = None,
        email: Optional[str] = None,
        company_name: Optional[str] = None,
        address: Optional[str] = None,
        country_code_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Takes any combination of input data and returns:
        {
            "success": bool,
            "prefill": {...},      # what can be immediately filled in the form
            "services": {...},     # raw service responses
            "messages": [...],     # explanations for UI
        }
        """

        prefills: Dict[str, Any] = {}
        services: Dict[str, Any] = {}
        messages = []

        vat_number = (vat_number or "").strip()
        domain = (domain or "").strip()
        email = (email or "").strip()
        company_name = (company_name or "").strip()
        address = (address or "").strip()

        # 1) If VAT is provided — this is the main key
        if vat_number:
            try:
                vat_result = self.vat_lookup.lookup(
                    vat_number=vat_number,
                    country_code=country_code_hint,
                    company_name_hint=company_name or None,
                )
                services["vat_lookup"] = vat_result

                pre = vat_result.get("prefill") or {}
                prefills.update({k: v for k, v in pre.items() if v})

                if vat_result.get("messages"):
                    messages.extend(vat_result["messages"])
            except ValueError as e:
                messages.append({"level": "danger", "text": str(e)})
                return {
                    "success": False,
                    "prefill": {},
                    "services": {},
                    "messages": messages,
                }

        # 2) If domain or email is provided — connect OSINT scanner
        target_domain = None
        if domain:
            target_domain = domain
        elif email and "@" in email:
            target_domain = email.split("@", 1)[1]
        else:
            # Use company name from VAT lookup or from parameter
            company_for_domain = prefills.get("counterparty_name") or company_name
            if company_for_domain and company_for_domain not in ['---', 'N/A', 'Unknown', '']:
                # Try to extract domain from company name (e.g., "Google GmbH" -> "google.de")
                target_domain = self._guess_domain_from_company_name(
                    company_for_domain, 
                    prefills.get("counterparty_country") or country_code_hint
                )

        if target_domain:
            try:
                osint = OsintScanner(domain=target_domain)
                osint_results = osint.run_all()
                services["osint"] = osint_results

                # Extract possible company names/country/city from Whois/SSL (as hints)
                extracted = self._extract_from_osint(osint_results)
                for key, value in extracted.items():
                    prefills.setdefault(key, value)

                messages.append(f"OSINT-Analyse für {target_domain} durchgeführt (Whois/DNS/SSL/Headers).")
            except Exception as e:
                # Don't block the whole process if OSINT fails
                messages.append(f"OSINT-Scan fehlgeschlagen: {str(e)}")

        # 3) If company_name / address / country_code_hint is provided — try registries directly
        #    (without paid APIs, only those already implemented)
        if company_name and (country_code_hint or vat_number or address):
            cc = (country_code_hint or prefills.get("counterparty_country") or "").upper()
            if cc:
                reg = self.registry_manager.lookup(
                    country_code=cc,
                    company_name=company_name,
                    vat_number=prefills.get("counterparty_vat") or vat_number or None,
                )
                if reg:
                    services[f"registry_{cc.lower()}"] = reg
                    data = reg.get("data") or {}
                    for field, value in {
                        "counterparty_name": data.get("company_name"),
                        "counterparty_address": data.get("address"),
                    }.items():
                        if value and not prefills.get(field):
                            prefills[field] = value
                    messages.append(f"Eintrag im Handelsregister gefunden ({cc}).")

        # 4) Final response
        if not prefills and not services:
            return {
                "success": False,
                "prefill": {},
                "services": {},
                "messages": ["Keine Daten in kostenlosen Quellen gefunden."],
            }

        return {
            "success": True,
            "prefill": prefills,
            "services": services,
            "messages": messages,
        }

    # ------------------ INTERNAL METHODS ------------------
    def _extract_from_osint(self, results: Any) -> Dict[str, str]:
        """
        Very carefully extract hints from OSINT results:
        company name, country, city.
        """
        extracted: Dict[str, str] = {}

        if not isinstance(results, list):
            return extracted

        for item in results:
            service = (item.get("service") or "").lower()
            data = item.get("data") or item.get("details") or {}

            # Whois → Organization / Country
            if service == "whois" and isinstance(data, dict):
                org = data.get("org") or data.get("organization")
                country = data.get("country")
                city = data.get("city")
                if org and not extracted.get("counterparty_name"):
                    extracted["counterparty_name"] = org
                if country and not extracted.get("counterparty_country"):
                    extracted["counterparty_country"] = country
                if city and not extracted.get("counterparty_city"):
                    extracted["counterparty_city"] = city

        return extracted

    def _guess_domain_from_company_name(self, company_name: str, country_code: Optional[str] = None) -> Optional[str]:
        """
        Спроба здогадатися про домен компанії з її назви.
        Наприклад: "Google GmbH" -> "google.de"
        """
        import re
        
        if not company_name:
            return None
        
        # Видаляємо юридичні форми та спецсимволи
        cleaned = re.sub(
            r'\b(GmbH|AG|Ltd|LLC|Inc|Corp|SE|KG|OHG|eV|e\.V\.|UG|mbH)\b',
            '',
            company_name,
            flags=re.IGNORECASE
        ).strip()
        
        # Видаляємо спецсимволи та пробіли
        cleaned = re.sub(r'[^\w\s-]', '', cleaned)
        cleaned = re.sub(r'\s+', '', cleaned).lower()
        
        if not cleaned or len(cleaned) < 3:
            return None
        
        # Визначаємо TLD за країною
        tld_map = {
            'DE': 'de', 'AT': 'at', 'CH': 'ch', 'FR': 'fr', 'IT': 'it',
            'ES': 'es', 'NL': 'nl', 'BE': 'be', 'PL': 'pl', 'CZ': 'cz',
            'GB': 'uk', 'UK': 'uk', 'US': 'com', 'CA': 'ca', 'UA': 'ua'
        }
        
        tld = tld_map.get(country_code.upper() if country_code else '', 'com')
        guessed_domain = f"{cleaned}.{tld}"
        
        return guessed_domain
