"""
Programmatic SEO Data Generator
Генерує дані для сотень SEO-оптимізованих сторінок
Формула: VAT Check для {ТИП БІЗНЕСУ} у {МІСТО}
"""

import json
import os

# Типи бізнесу з реальними болями
BUSINESS_TYPES = {
    "gmbh": {
        "de_name": "GmbH",
        "ru_name": "ООО",
        "en_name": "Limited Company",
        "pain_points": [
            "Wie führe ich eine VAT-Prüfung für eine GmbH durch?",
            "Welche VAT-Nummern gelten für GmbHs in Deutschland?",
            "Wie verifiziere ich die Steuernummer eines GmbH-Partners?"
        ],
        "use_case": "Anna hat eine GmbH mit 12 Mitarbeitern. Sie benötigte eine schnelle VAT-Verifizierung für neue Lieferanten aus der EU."
    },
    "freiberufler": {
        "de_name": "Freiberufler",
        "ru_name": "Фрилансер",
        "en_name": "Freelancer",
        "pain_points": [
            "Bin ich als Freiberufler zur Registrierung einer VAT-Nummer verpflichtet?",
            "Wie überprüfe ich die VAT-Nummer eines internationalen Freiberuflers?",
            "Welche Compliance-Anforderungen gelten für Freiberufler?"
        ],
        "use_case": "Marcus ist Grafik-Designer und arbeitet mit Kunden aus Frankreich. Er nutzt VAT Verifizierung zur schnellen Überprüfung seiner Kunden."
    },
    "online-shop": {
        "de_name": "Online-Shop",
        "ru_name": "Интернет-магазин",
        "en_name": "E-commerce Store",
        "pain_points": [
            "Wie führe ich VAT-Checks für internationale Shop-Kunden durch?",
            "Welche Compliance-Risiken bestehen für Online-Shops?",
            "Wie verifiziere ich VAT-Nummern automatisiert?"
        ],
        "use_case": "TechShop24 verkauft online an 15 Länder. Mit VAT Verifizierung sparen sie täglich 2 Stunden bei Kundenchecks."
    },
    "einzelunternehmer": {
        "de_name": "Einzelunternehmer",
        "ru_name": "ИП",
        "en_name": "Sole Proprietor",
        "pain_points": [
            "Muss ich als Einzelunternehmer eine VAT-Nummer anmelden?",
            "Wie überprüfe ich, ob ein Einzelunternehmer registriert ist?",
            "Welche steuerlichen Anforderungen gelten?"
        ],
        "use_case": "Peter betreibt einen Handwerksbetrieb. Er verifiziert Subunternehmer mit unserem Tool in Sekunden."
    },
    "startup": {
        "de_name": "Startup",
        "ru_name": "Стартап",
        "en_name": "Startup",
        "pain_points": [
            "Welche VAT-Compliance ist für junge Startups wichtig?",
            "Wie überprüfe ich die Legalität von B2B-Partnern?",
            "Welche Risiken entstehen durch falsche Partner-Verifizierung?"
        ],
        "use_case": "Ein SaaS-Startup brauchte schnell Partner zu verifizieren. Mit unserem Tool in weniger als 1 Woche ready für Enterprise-Kunden."
    },
    "kmu": {
        "de_name": "KMU/Mittelstand",
        "ru_name": "МСП",
        "en_name": "SMB/Mid-market",
        "pain_points": [
            "Wie implementiere ich VAT-Compliance in meinem Unternehmen?",
            "Welche automatisierten Tools gibt es für VAT-Checks?",
            "Wie minimiere ich Compliance-Risiken?"
        ],
        "use_case": "Ein Maschinenbau-Mittelständler wurde von Behörden geprüft. Jetzt nutzen sie VAT Verifizierung für alle neuen Geschäftspartner."
    }
}

# Главные немецкие города (уже 20+)
CITIES = {
    "berlin": {"de_name": "Berlin", "region": "Berlin", "population": "3.6M"},
    "munich": {"de_name": "München", "region": "Bavaria", "population": "1.5M"},
    "frankfurt": {"de_name": "Frankfurt am Main", "region": "Hesse", "population": "746K"},
    "hamburg": {"de_name": "Hamburg", "region": "Hamburg", "population": "1.9M"},
    "cologne": {"de_name": "Köln", "region": "North Rhine-Westphalia", "population": "1.1M"},
    "dusseldorf": {"de_name": "Düsseldorf", "region": "North Rhine-Westphalia", "population": "621K"},
    "dortmund": {"de_name": "Dortmund", "region": "North Rhine-Westphalia", "population": "586K"},
    "essen": {"de_name": "Essen", "region": "North Rhine-Westphalia", "population": "582K"},
    "stuttgart": {"de_name": "Stuttgart", "region": "Baden-Württemberg", "population": "623K"},
    "karlsruhe": {"de_name": "Karlsruhe", "region": "Baden-Württemberg", "population": "315K"},
    "heidelberg": {"de_name": "Heidelberg", "region": "Baden-Württemberg", "population": "160K"},
    "mannheim": {"de_name": "Mannheim", "region": "Baden-Württemberg", "population": "308K"},
    "leipzig": {"de_name": "Leipzig", "region": "Saxony", "population": "622K"},
    "dresden": {"de_name": "Dresden", "region": "Saxony", "population": "556K"},
    "nuremberg": {"de_name": "Nürnberg", "region": "Bavaria", "population": "518K"},
    "augsburg": {"de_name": "Augsburg", "region": "Bavaria", "population": "296K"},
    "hanover": {"de_name": "Hannover", "region": "Lower Saxony", "population": "535K"},
    "bremen": {"de_name": "Bremen", "region": "Bremen", "population": "567K"},
    "hamburg": {"de_name": "Hamburg", "region": "Hamburg", "population": "1.9M"},
    "vienna": {"de_name": "Wien", "region": "Austria", "population": "1.9M"},  # Также важен
    "zurich": {"de_name": "Zürich", "region": "Switzerland", "population": "421K"},
    "amsterdam": {"de_name": "Amsterdam", "region": "Netherlands", "population": "873K"},
}

# Ключевые вопросы FAQ (2-3 для каждого типа + города)
FAQ_TEMPLATES = {
    "gmbh": [
        "Wie überprüfe ich die VAT-Nummer einer GmbH in {city}?",
        "Welche Unterlagen muss eine GmbH für VAT-Compliance bereit halten?",
        "Wie oft sollte ich VAT-Nummern von GmbH-Partnern überprüfen?",
        "Welche Strafen drohen bei falschen VAT-Angaben von GmbHs?"
    ],
    "freiberufler": [
        "Muss ein Freiberufler in {city} eine VAT-Nummer haben?",
        "Wie unterscheide ich legale von illegalen Freelancer-Anbietern?",
        "Welche Dokumentation brauche ich von Freelancern?",
        "Wie prüfe ich die Steuernummer eines Freiberuflers?"
    ],
    "online-shop": [
        "Welche VAT-Compliance ist für meinen Online-Shop erforderlich?",
        "Wie automatisiere ich VAT-Checks im Online-Shop?",
        "Welche Haftung habe ich für falsche Partner-Angaben?",
        "Wie implementiere ich VATIDS-Prüfung bei Checkout?"
    ],
    "einzelunternehmer": [
        "Wie überprüfe ich, ob ein Einzelunternehmer registriert ist?",
        "Gibt es Unterschiede bei VAT-Checks für Einzelunternehmer?",
        "Wie lange dauert eine VAT-Verifizierung?",
        "Was tun wenn ein Einzelunternehmer keine VAT-Nummer hat?"
    ],
    "startup": [
        "Welche Compliance braucht mein Startup von Anfang an?",
        "Wie überprüfe ich B2B-Partner systematisch?",
        "Welche Risiken entstehen durch schlechte Partner-Vetting?",
        "Wie scale ich Compliance bei schnellem Wachstum?"
    ],
    "kmu": [
        "Wie implementiere ich VAT-Compliance in meiner KMU?",
        "Welche automatisierten Tools helfen bei Compliance?",
        "Wie reduziere ich Compliance-Risiken?",
        "Welche EU-VAT-Regeln muss meine KMU kennen?"
    ]
}

def generate_page_data():
    """Генерирует данные для всех Programmatic SEO страниц"""
    pages = []
    
    for business_slug, business in BUSINESS_TYPES.items():
        for city_slug, city in CITIES.items():
            page = {
                "slug": f"{business_slug}-{city_slug}",
                "url": f"/vat-check/{business_slug}-{city_slug}",
                "title": f"VAT Check für {business['de_name']} in {city['de_name']} | VAT Verifizierung",
                "meta_description": f"Schnelle und sichere VAT-Verifizierung für {business['de_name']}s in {city['de_name']}. VIES-Datenbank + Sanktionsprüfung in unter 5 Sekunden.",
                "h1": f"VAT Check für {business['de_name']} in {city['de_name']}",
                "intro_text": f"Sie führen ein {business['de_name']} in {city['de_name']} und benötigen sichere VAT-Verifikation? Mit unserem Tool überprüfen Sie europäische Geschäftspartner in Sekunden. Kostenlos für die erste Prüfung.",
                
                # SEO Keywords
                "main_keyword": f"VAT Check {business['de_name']} {city['de_name']}",
                "long_tail_keywords": [
                    f"USt-IdNr prüfen {business['de_name']} {city['de_name']}",
                    f"VIES Abfrage {business['de_name']} {city['de_name']}",
                    f"Steuernummer verifizieren {business['de_name']} {city['de_name']}",
                    f"VAT Compliance {business['de_name']} {city['de_name']}"
                ],
                
                # Реальный кейс
                "case_study": business['use_case'],
                
                # FAQ (специфичные для комбинации business + city)
                "faq": [
                    {
                        "question": question.replace("{city}", city['de_name']),
                        "answer": f"Mit VAT Verifizierung überprüfen Sie VAT-Nummern in {city['de_name']} automatisiert. Unsere Plattform verbindet sich direkt mit der VIES-Datenbank und prüft die Legalität von {business['de_name']}s. Sie erhalten das Resultat in unter 5 Sekunden."
                    }
                    for question in FAQ_TEMPLATES.get(business_slug, FAQ_TEMPLATES['gmbh'])[:3]
                ],
                
                # Schema.org
                "schema": {
                    "@context": "https://schema.org",
                    "@type": "FAQPage",
                    "mainEntity": [
                        {
                            "@type": "Question",
                            "name": faq['question'],
                            "acceptedAnswer": {
                                "@type": "Answer",
                                "text": faq['answer']
                            }
                        }
                        for faq in [
                            {
                                "question": question.replace("{city}", city['de_name']),
                                "answer": f"Mit VAT Verifizierung überprüfen Sie VAT-Nummern in {city['de_name']} automatisiert. Unsere Plattform verbindet sich direkt mit der VIES-Datenbank und prüft die Legalität von {business['de_name']}s. Sie erhalten das Resultat in unter 5 Sekunden."
                            }
                            for question in FAQ_TEMPLATES.get(business_slug, FAQ_TEMPLATES['gmbh'])[:3]
                        ]
                    ]
                },
                
                # CTA
                "cta_text": "Kostenlos testen",
                "cta_button": "VAT Jetzt überprüfen"
            }
            pages.append(page)
    
    return pages

def save_to_json(pages):
    """Сохраняет страницы в JSON файл"""
    output_file = "programmatic_seo_pages.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)
    print(f"✅ {len(pages)} страниц сохранено в {output_file}")
    return output_file

def print_summary(pages):
    """Выводит статистику"""
    print("\n📊 Programmatic SEO Data Summary:")
    print(f"   Total pages: {len(pages)}")
    print(f"   Business types: {len(BUSINESS_TYPES)}")
    print(f"   Cities: {len(CITIES)}")
    print(f"   Combination: {len(BUSINESS_TYPES)} × {len(CITIES)} = {len(pages)} сторіние")
    
    print("\n📍 Sample pages:")
    for i in range(min(3, len(pages))):
        page = pages[i]
        print(f"   - {page['url']}")
        print(f"     Title: {page['title'][:60]}...")

if __name__ == "__main__":
    pages = generate_page_data()
    save_to_json(pages)
    print_summary(pages)
