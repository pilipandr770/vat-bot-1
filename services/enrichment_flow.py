# FILE: services/enrichment_flow.py

from __future__ import annotations
from typing import Optional, Dict, Any

from services.vat_lookup import VatLookupService
from services.business_registry import BusinessRegistryManager
from services.osint.scanner import OsintScanner


class EnrichmentOrchestrator:
    """
    Єдина точка входу для автодоповнення даних контрагента.
    Працює з безкоштовними джерелами:
    - VIES
    - Бізнес-реєстри (DE/CZ/PL)
    - OSINT по домену/e-mail (Whois, DNS, SSL, headers, соцмережі)
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
        Приймає будь-яку комбінацію вхідних даних і повертає:
        {
            "success": bool,
            "prefill": {...},      # що можна одразу підставити у форму
            "services": {...},     # сирі відповіді сервісів
            "messages": [...],     # пояснення для UI
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

        # 1) Якщо є VAT — це головний ключ
        if vat_number:
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

        # 2) Якщо є домен або email — підключаємо OSINT-сканер
        target_domain = None
        if domain:
            target_domain = domain
        elif email and "@" in email:
            target_domain = email.split("@", 1)[1]
        else:
            # Використовуємо назву компанії з VAT lookup або з параметра
            company_for_domain = prefills.get("counterparty_name") or company_name
            if company_for_domain and company_for_domain not in ['---', 'N/A', 'Unknown', '']:
                # Спроба витягти домен з назви компанії (наприклад, "Google GmbH" -> "google.de")
                target_domain = self._guess_domain_from_company_name(
                    company_for_domain, 
                    prefills.get("counterparty_country") or country_code_hint
                )

        if target_domain:
            try:
                osint = OsintScanner(domain=target_domain)
                osint_results = osint.run_all()
                services["osint"] = osint_results

                # Витягуємо можливі імена компанії/країну/місто з Whois/SSL (як підказки)
                extracted = self._extract_from_osint(osint_results)
                for key, value in extracted.items():
                    prefills.setdefault(key, value)

                messages.append(f"OSINT-аналіз для {target_domain} виконано (Whois/DNS/SSL/Headers).")
            except Exception as e:
                # Не блокуємо весь процес, якщо OSINT не спрацював
                messages.append(f"OSINT-сканування не вдалося: {str(e)}")

        # 3) Якщо є company_name / address / country_code_hint — пробуємо реєстри напряму
        #    (без платних API, тільки ті, що вже реалізовані)
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
                    messages.append(f"Знайдено запис у державному реєстрі ({cc}).")

        # 4) Фінальна відповідь
        if not prefills and not services:
            return {
                "success": False,
                "prefill": {},
                "services": {},
                "messages": ["За наданими даними нічого не знайдено в безкоштовних джерелах."],
            }

        return {
            "success": True,
            "prefill": prefills,
            "services": services,
            "messages": messages,
        }

    # ------------------ ВНУТРІШНІ МЕТОДИ ------------------
    def _extract_from_osint(self, results: Any) -> Dict[str, str]:
        """
        Дуже обережно дістаємо підказки з OSINT-результатів:
        назву компанії, країну, місто.
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
            'GB': 'uk', 'UK': 'uk', 'US': 'com', 'CA': 'ca'
        }
        
        tld = tld_map.get(country_code.upper() if country_code else '', 'com')
        guessed_domain = f"{cleaned}.{tld}"
        
        return guessed_domain
