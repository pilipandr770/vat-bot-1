"""
Blog Generator Service
======================
Täglich generiert der Dienst einen SEO-optimierten Artikel auf Deutsch zum Thema
"sicheres Wirtschaften / B2B-Compliance / Betrugsschutz".

Strategie (Prioritäten):
1. Wenn ein relevantes RSS-Element gefunden wird → Artikel basiert auf dem Thema der News.
2. Andernfalls → nächstes Topic aus der vordefinierten SEO-Keyword-Liste.

Quellen (RSS):
  - BSI Sicherheitshinweise (DE Bundesamt für Sicherheit in der Informationstechnik)
  - BaFin Verbraucherwarnungen
  - EUR-Lex press releases (EU VAT / sanctions)

GPT-4o-mini generiert ~900-1200 Wörter Fließtext + HTML-Markup.
"""

import os
import re
import json
import logging
import hashlib
import html
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import requests

logger = logging.getLogger(__name__)

# ─── RSS Feed URLs ────────────────────────────────────────────────────────────
RSS_FEEDS = [
    {
        "url": "https://www.bsi.bund.de/SiteGlobals/Functions/RSSFeed/RSSNewsfeed/RSSNewsfeed_Sicherheitshinweise.xml",
        "name": "BSI Sicherheitshinweise",
        "relevance_keywords": ["betrug", "sicherheit", "warnung", "phishing", "sanktion", "identität",
                                "compliance", "datenschutz", "unternehmen", "b2b", "rechnung", "zahlung"],
    },
    {
        "url": "https://www.bafin.de/SiteGlobals/Functions/RSSFeed/DE/RSSNewsfeed_Verbraucherwarnung.xml",
        "name": "BaFin Verbraucherwarnungen",
        "relevance_keywords": ["warnung", "betrug", "unternehmen", "lizenz", "investition", "finanz"],
    },
    {
        "url": "https://ec.europa.eu/taxation_customs/news_rss_en",
        "name": "EU Taxation News",
        "relevance_keywords": ["vat", "sanctions", "compliance", "fraud", "business", "registration"],
    },
]

# ─── SEO Topic Schedule (50+ topics) ─────────────────────────────────────────
# Format: (title_de, main_keyword, category, tags)
SEO_TOPICS = [
    # VAT & Compliance
    ("Wie prüft man eine VAT-Nummer korrekt? Schritt-für-Schritt-Anleitung",
     "VAT-Nummer prüfen Deutschland", "vat-compliance",
     ["USt-IdNr", "VIES", "VAT-Verifizierung", "Deutschland"]),
    ("VIES-Datenbank: Das offizielle EU-Tool zur Umsatzsteuer-Prüfung erklärt",
     "VIES Datenbank erklärt", "vat-compliance",
     ["VIES", "EU-Steuer", "USt-IdNr", "Umsatzsteuer"]),
    ("USt-IdNr. Verifizierung: Warum jedes deutsche Unternehmen das tun sollte",
     "USt-IdNr verifizieren Pflicht", "vat-compliance",
     ["Umsatzsteuer", "B2B", "Steuerpflicht", "Compliance"]),
    ("Reverse-Charge-Verfahren: Wie VAT-Verifizierung Steuerrisiken reduziert",
     "Reverse Charge VAT Prüfung", "vat-compliance",
     ["Reverse Charge", "EU-Steuer", "B2B-Handel", "Vorsteuerabzug"]),
    ("EU VAT-Betrug: Karussellgeschäfte erkennen und vermeiden",
     "EU VAT-Betrug erkennen", "fraud-prevention",
     ["Karussellbetrug", "USt-Betrug", "VIES", "B2B-Sicherheit"]),

    # Sanctions
    ("EU-Sanktionsliste 2025: Was Unternehmen jetzt wissen müssen",
     "EU-Sanktionsliste Unternehmen 2025", "sanctions",
     ["Sanktionen", "EU", "Compliance", "Russland", "Iran"]),
    ("OFAC-Sanktionen: Auswirkungen auf deutsche Exporteure",
     "OFAC Sanktionen Deutschland", "sanctions",
     ["OFAC", "US-Sanktionen", "Export-Compliance", "Wirtschaftssanktionen"]),
    ("Sanktionsprüfung von Geschäftspartnern: Rechtliche Pflicht oder Best Practice?",
     "Sanktionsprüfung Geschäftspartner Pflicht", "sanctions",
     ["Sanktionen", "Due Diligence", "Compliance", "KYC"]),
    ("Wie automatisierte Sanktionsprüfung Ihren Compliance-Aufwand halbiert",
     "automatische Sanktionsprüfung Software", "sanctions",
     ["Sanktionsscreening", "Automatisierung", "B2B-Compliance", "KYC"]),
    ("UK-Sanktionen nach Brexit: Was deutsche Unternehmen beachten müssen",
     "UK-Sanktionen Brexit Deutschland", "sanctions",
     ["Brexit", "UK-Sanktionen", "OFSI", "Exportkontrolle"]),

    # Fraud Prevention / B2B Safety
    ("5 häufige Betrugsmaschen beim B2B-Handel in Deutschland 2025",
     "B2B Betrug Deutschland erkennen 2025", "fraud-prevention",
     ["B2B-Betrug", "Fake-Rechnung", "Identitätsbetrug", "Sicherheit"]),
    ("CEO-Fraud: So schützen Sie Ihr Unternehmen vor gefälschten Chef-E-Mails",
     "CEO Fraud Deutschland Schutz", "fraud-prevention",
     ["CEO-Fraud", "Business Email Compromise", "E-Mail-Sicherheit", "Phishing"]),
    ("Fake-Lieferanten erkennen: 8 Warnsignale bei neuen Geschäftspartnern",
     "Fake Lieferanten erkennen Warnsignale", "fraud-prevention",
     ["Lieferantenbetrug", "Due Diligence", "B2B-Sicherheit", "KYC"]),
    ("Identitätsbetrug im B2B: Wenn sich jemand als bekanntes Unternehmen ausgibt",
     "Identitätsbetrug B2B Unternehmen verhindern", "fraud-prevention",
     ["Identitätsbetrug", "Firmenbetrug", "B2B", "Verifizierung"]),
    ("Rechnungsbetrug erkennen und verhindern: Leitfaden für KMU",
     "Rechnungsbetrug erkennen KMU", "fraud-prevention",
     ["Rechnungsbetrug", "Fake-IBAN", "KMU", "Finanzschutz"]),
    ("Insolvenz-Betrug: Wie schützen Sie sich, bevor der Schaden eintritt?",
     "Insolvenz Betrug Geschäftspartner erkennen", "fraud-prevention",
     ["Insolvenz", "Kreditrisiko", "Due Diligence", "B2B"]),

    # OSINT & Due Diligence
    ("OSINT für Unternehmen: Open-Source-Intelligence bei der Partnerpüfung",
     "OSINT Unternehmensverifikation Anleitung", "osint",
     ["OSINT", "Open Source Intelligence", "Due Diligence", "B2B"]),
    ("WHOIS-Analyse: Was der Domains-Check über einen Geschäftspartner verrät",
     "WHOIS Analyse Geschäftspartner prüfen", "osint",
     ["WHOIS", "Domain", "OSINT", "Unternehmenscheck"]),
    ("SSL-Zertifikat als Vertrauensindikator: Stimmt das noch?",
     "SSL-Zertifikat Unternehmen Vertrauen prüfen", "osint",
     ["SSL", "HTTPS", "Websicherheit", "Phishing-Erkennung"]),
    ("DNS-Analyse im B2B: Warnsignale in der Domainstruktur erkennen",
     "DNS Analyse B2B Unternehmen prüfen", "osint",
     ["DNS", "OSINT", "Domain-Sicherheit", "B2B-Prüfung"]),

    # GDPR / Data Protection
    ("DSGVO im B2B: Was müssen Unternehmen bei der Datenweitergabe beachten?",
     "DSGVO B2B Datenweitergabe Unternehmen", "gdpr",
     ["DSGVO", "GDPR", "B2B", "Datenschutz"]),
    ("Datenschutz-Compliance-Prüfung bei Neukunden: Eine Checkliste",
     "Datenschutz Compliance Neukunden Checkliste", "gdpr",
     ["DSGVO", "Compliance", "Checkliste", "KYC"]),
    ("Auftragsverarbeitung: Wann braucht man einen AV-Vertrag?",
     "Auftragsverarbeitung AV-Vertrag wann notwendig", "gdpr",
     ["DSGVO", "Auftragsverarbeitung", "B2B", "Vertrag"]),

    # Handelsregister & KYC
    ("Handelsregister-Abfrage: Pflicht oder freiwillig bei Neukunden?",
     "Handelsregister Abfrage Pflicht Neukunden", "kyc",
     ["Handelsregister", "KYC", "GmbH-Prüfung", "Due Diligence"]),
    ("GmbH vs. UG: Unterschiede in der Geschäftspartner-Verifizierung",
     "GmbH UG Unterschied Verifizierung prüfen", "kyc",
     ["GmbH", "UG", "Handelsregister", "Unternehmensform"]),
    ("KYC Know Your Customer: Anforderungen für deutsche KMU erklärt",
     "KYC Know Your Customer KMU Deutschland", "kyc",
     ["KYC", "Know Your Customer", "KMU", "Compliance"]),
    ("Wie prüft man ausländische Unternehmen? EU-Handelsregister im Überblick",
     "ausländische Unternehmen prüfen EU Handelsregister", "kyc",
     ["EU-Handelsregister", "KYC", "internationale Partner", "Due Diligence"]),
    ("Transparenzregister: Wer muss sich eintragen? Was müssen Käufer prüfen?",
     "Transparenzregister Deutschland erklärt prüfen", "kyc",
     ["Transparenzregister", "Geldwäscheprävention", "Eigentümerstruktur", "KYC"]),

    # Email Security
    ("Phishing-E-Mails im B2B: Erkennungsmerkmale und Schutzmaßnahmen",
     "Phishing E-Mail B2B erkennen schützen", "email-security",
     ["Phishing", "E-Mail-Betrug", "B2B", "IT-Sicherheit"]),
    ("Business Email Compromise (BEC): So schützt sich Ihr Unternehmen",
     "Business Email Compromise BEC Schutz Deutschland", "email-security",
     ["BEC", "CEO-Fraud", "E-Mail-Sicherheit", "DMARC"]),
    ("DMARC, DKIM, SPF: E-Mail-Authentifizierung einfach erklärt",
     "DMARC DKIM SPF E-Mail-Sicherheit erklärt", "email-security",
     ["DMARC", "DKIM", "SPF", "E-Mail-Schutz"]),
    ("VirusTotal für Unternehmen: Anhänge automatisch auf Malware prüfen",
     "VirusTotal Anhänge Malware prüfen Unternehmen", "email-security",
     ["VirusTotal", "Malware", "E-Mail-Sicherheit", "Anhänge"]),

    # Phone / Spam
    ("Spam-Anrufe im Business: Wie erkennt man betrügerische Telefonnummern?",
     "Spam-Anrufe Unternehmen erkennen Deutschland", "phone-security",
     ["Spam-Anrufe", "Telefonbetrug", "Phone Intelligence", "Deutschland"]),
    ("Telefonbetrug 2025: Neue Maschen und wie man sie erkennt",
     "Telefonbetrug neue Maschen 2025 erkennen", "phone-security",
     ["Telefonbetrug", "Vishing", "Scam Detection", "B2B"]),
    ("FTC und BNetzA: Welche Behörden gegen Spam-Anrufe vorgehen",
     "FTC BNetzA Spam-Anrufe Behörden Deutschland USA", "phone-security",
     ["BNetzA", "FTC", "Spam-Nummern", "Verbraucherschutz"]),

    # General B2B Security / SaaS
    ("Due Diligence kompakt: 10-Punkte-Checkliste für neue Geschäftspartner",
     "Due Diligence Checkliste Geschäftspartner 10 Punkte", "due-diligence",
     ["Due Diligence", "Checkliste", "B2B", "Partnerprüfung"]),
    ("Compliance-Management für KMU: Einstieg ohne Großkonzern-Budget",
     "Compliance Management KMU Deutschland günstig", "due-diligence",
     ["Compliance", "KMU", "Management", "Budget"]),
    ("Warum Lieferkettengesetz auch kleinere Unternehmen betrifft",
     "Lieferkettengesetz KMU Auswirkungen Deutschland", "due-diligence",
     ["Lieferkettengesetz", "LkSG", "KMU", "Compliance"]),
    ("AML (Anti-Geldwäsche) Pflichten für gewerbliche Unternehmen in Deutschland",
     "AML Anti-Geldwäsche Pflichten Unternehmen Deutschland", "due-diligence",
     ["Geldwäsche", "AML", "KYC", "Compliance"]),
    ("Warum Automatisierung die Geschäftspartner-Prüfung revolutioniert",
     "Automatisierung Geschäftspartner Verifizierung SaaS", "due-diligence",
     ["Automatisierung", "SaaS", "B2B-Verifizierung", "API"]),

    # Deutschland-spezifisch / SEO Geo
    ("Sicher Geschäfte machen in Deutschland: Ein Leitfaden für ausländische Unternehmen",
     "sicher Geschäfte machen Deutschland Ausland", "geo-germany",
     ["Deutschland", "B2B", "Sicherheit", "ausländische Unternehmen"]),
    ("B2B-Handel mit deutschen GmbHs: Worauf Sie achten sollten",
     "B2B Handel GmbH Deutschland Tipps", "geo-germany",
     ["GmbH", "B2B-Handel", "Deutschland", "Due Diligence"]),
    ("Berlin, Hamburg, München: Regionale Unternehmensrisiken kennen und vermeiden",
     "Unternehmensrisiken Deutschland regionale Unterschiede", "geo-germany",
     ["Berlin", "Hamburg", "München", "Risikobewertung"]),
    ("Exportkontrolle: Was deutsche Exporteure vor jedem Geschäft prüfen müssen",
     "Exportkontrolle Deutschland Exporteur Pflicht", "geo-germany",
     ["Exportkontrolle", "Außenwirtschaft", "AWG", "Compliance"]),

    # FinTech / Payments
    ("IBAN-Betrug verhindern: Wie Sie Bankdaten von Geschäftspartnern verifizieren",
     "IBAN-Betrug verhindern Bankdaten verifizieren", "payments",
     ["IBAN", "Bankbetrug", "Zahlungssicherheit", "B2B"]),
    ("Vorkasse-Betrug: Wenn Lieferanten plötzlich neue Kontonummern mitteilen",
     "Vorkasse Betrug neue Bankverbindung erkennen", "payments",
     ["Vorkasse", "Bankbetrug", "Fake-Rechnung", "B2B-Sicherheit"]),

    # Pentesting / Website Safety
    ("Website-Sicherheits-Audit: Warum auch KMU regelmäßig scannen sollten",
     "Website Sicherheits-Audit KMU Scanner", "website-security",
     ["Vulnerability Scanner", "Website-Sicherheit", "KMU", "Pentesting"]),
    ("CVE-Sicherheitslücken 2025: Welche Unternehmenssoftware besonders betroffen ist",
     "CVE Sicherheitslücken Unternehmenssoftware 2025", "website-security",
     ["CVE", "Sicherheitslücken", "Patch Management", "IT-Sicherheit"]),
    ("OWASP Top 10: Die größten Web-App-Risiken erklärt",
     "OWASP Top 10 Web App Risiken erklärt deutsch", "website-security",
     ["OWASP", "Web-Sicherheit", "Pentest", "Schwachstellen"]),
]

CATEGORY_LABELS = {
    "vat-compliance": "USt & Compliance",
    "sanctions": "Sanktionen",
    "fraud-prevention": "Betrugsschutz",
    "osint": "OSINT & Intelligence",
    "gdpr": "DSGVO & Datenschutz",
    "kyc": "KYC & Handelsregister",
    "email-security": "E-Mail-Sicherheit",
    "phone-security": "Telefon-Sicherheit",
    "due-diligence": "Due Diligence",
    "geo-germany": "Sicher in Deutschland",
    "payments": "Zahlungssicherheit",
    "website-security": "Website-Sicherheit",
}


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[äÄ]', 'ae', text)
    text = re.sub(r'[öÖ]', 'oe', text)
    text = re.sub(r'[üÜ]', 'ue', text)
    text = re.sub(r'[ß]', 'ss', text)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text).strip('-')
    return text[:200]


def _fetch_rss_topics(max_age_hours: int = 48) -> Optional[Dict]:
    """Try to fetch a relevant topic from configured RSS feeds. Returns first match or None."""
    cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
    for feed_config in RSS_FEEDS:
        try:
            resp = requests.get(feed_config["url"], timeout=6,
                                headers={"User-Agent": "VATVerifizierung-BlogBot/1.0"})
            if resp.status_code != 200:
                continue
            # Simple XML parse without feedparser dependency
            from xml.etree import ElementTree as ET
            root = ET.fromstring(resp.content)
            namespace = ''
            items = root.findall('./channel/item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
            for item in items[:10]:
                title_el = item.find('title') or item.find('{http://www.w3.org/2005/Atom}title')
                link_el = item.find('link') or item.find('{http://www.w3.org/2005/Atom}link')
                desc_el = (item.find('description') or item.find('summary')
                           or item.find('{http://www.w3.org/2005/Atom}summary'))
                if title_el is None:
                    continue
                title_text = (title_el.text or '').strip()
                link_text = (link_el.text if link_el is not None and link_el.text else
                             (link_el.get('href', '') if link_el is not None else ''))
                desc_text = html.unescape((desc_el.text or '') if desc_el is not None else '')

                combined = (title_text + ' ' + desc_text).lower()
                hit = any(kw.lower() in combined for kw in feed_config["relevance_keywords"])
                if hit:
                    logger.info(f"RSS match from {feed_config['name']}: {title_text[:80]}")
                    return {
                        "source_title": title_text,
                        "source_url": link_text,
                        "source_name": feed_config["name"],
                        "summary": desc_text[:500],
                    }
        except Exception as e:
            logger.debug(f"RSS fetch failed for {feed_config['name']}: {e}")
    return None


def _pick_topic_from_schedule(app) -> Dict:
    """Pick the next topic from SEO_TOPICS that hasn't been used yet."""
    from crm.models import BlogPost
    used_slugs = {row[0] for row in app.extensions['sqlalchemy'].session.query(BlogPost.slug).all()}
    for topic in SEO_TOPICS:
        title, keyword, category, tags = topic
        candidate_slug = _slugify(title)
        if candidate_slug not in used_slugs:
            return {
                "title": title,
                "main_keyword": keyword,
                "category": category,
                "tags": tags,
            }
    # If all used, pick oldest slug by hashing position + date to get variety
    idx = (datetime.utcnow().timetuple().tm_yday) % len(SEO_TOPICS)
    title, keyword, category, tags = SEO_TOPICS[idx]
    return {"title": title, "main_keyword": keyword, "category": category, "tags": tags}


def _generate_article_with_openai(topic: Dict, rss_context: Optional[Dict]) -> Optional[str]:
    """Call OpenAI GPT-4o-mini to generate a German SEO article in HTML."""
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        logger.warning("OPENAI_API_KEY nicht gesetzt — Blog-Generierung übersprungen")
        return None

    title = topic.get("title", "")
    keyword = topic.get("main_keyword", title)
    tags = ", ".join(topic.get("tags", []))
    category = topic.get("category", "")

    rss_block = ""
    if rss_context:
        rss_block = f"""
Aktuelle Nachricht als Inspiration (nicht direkt zitieren, als Kontext nutzen):
Quelle: {rss_context.get('source_name', '')}
Titel: {rss_context.get('source_title', '')}
Zusammenfassung: {rss_context.get('summary', '')[:300]}
"""

    system_prompt = """Du bist ein SEO-Experte und Content-Autor, spezialisiert auf B2B-Sicherheit,
Compliance und Unternehmensverifizierung für den deutschen Markt. Du schreibst professionelle,
informative Artikel auf Deutsch für Entscheidungsträger (GeschäftsführerInnen, Compliance-Manager, CFOs).
Stil: sachlich-professionell, aber verständlich. Keine übertriebenen Werbetexte."""

    user_prompt = f"""Schreibe einen ausführlichen SEO-Blog-Artikel auf Deutsch.

Artikel-Titel: {title}
Haupt-Keyword: {keyword}
Kategorie: {category}
Verwandte Keywords: {tags}
{rss_block}

Anforderungen:
- Länge: 900-1200 Wörter
- Sprache: Deutsch (formell aber lesbar, Du-Form ist ok)
- Struktur: Einleitung → 4-5 Hauptabschnitte mit <h2>-Überschriften → Fazit
- Haupt-Keyword in Einleitung, mindestens 2 weiteren <h2>-Überschriften und im Fazit verwenden
- Konkrete Beispiele, Statistiken (plausibel), handlungsrelevante Tipps
- Bezüge zu VAT Verifizierung (https://vat-verifizierung.de) als Tool natürlich einweben
  (z.B. "Mit automatisierten Tools wie VAT Verifizierung...") — max. 2-3 Mal, nicht aufdringlich
- Am Ende: 1 FAQ-Block mit 3 Fragen/Antworten (für Featured Snippets) als <div class="faq-section">
- Gib NUR den HTML-Body zurück (kein <html>, <head> oder <body>-Tag)
- Verwende Bootstrap-kompatibles Markup: <h2>, <h3>, <p>, <ul>, <li>, <strong>
- FAQ: <div class="faq-section"><h3>Häufig gestellte Fragen</h3><dl><dt>Frage</dt><dd>Antwort</dd></dl></div>"""

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 2000,
                "temperature": 0.7,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        return content
    except Exception as e:
        logger.error(f"OpenAI Blog-Generierung fehlgeschlagen: {e}", exc_info=True)
        return None


def _estimate_read_time(html_content: str) -> int:
    """Estimate reading time in minutes (average 200 words/min)."""
    text = re.sub(r'<[^>]+>', '', html_content)
    words = len(text.split())
    return max(1, round(words / 200))


def _build_schema_markup(post_data: Dict) -> str:
    """Build JSON-LD Article schema markup."""
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post_data["title"],
        "description": post_data.get("meta_description", ""),
        "keywords": post_data.get("meta_keywords", ""),
        "datePublished": post_data["published_at"],
        "dateModified": post_data["published_at"],
        "author": {
            "@type": "Organization",
            "name": "VAT Verifizierung",
            "url": "https://vat-verifizierung.de"
        },
        "publisher": {
            "@type": "Organization",
            "name": "VAT Verifizierung",
            "logo": {
                "@type": "ImageObject",
                "url": "https://vat-verifizierung.de/static/images/logo.png"
            }
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"https://vat-verifizierung.de/blog/{post_data['slug']}"
        },
        "articleSection": CATEGORY_LABELS.get(post_data.get("category", ""), "Compliance"),
        "inLanguage": "de-DE"
    }, ensure_ascii=False)


def generate_daily_blog_post(app) -> bool:
    """
    Main entry point. Called by the scheduler daily.
    Returns True if a new post was created, False otherwise.
    """
    with app.app_context():
        from crm.models import db, BlogPost

        # Skip if already posted today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        existing_today = BlogPost.query.filter(BlogPost.generated_at >= today_start).first()
        if existing_today:
            logger.info("Blog: bereits ein Artikel heute generiert, überspringe")
            return False

        logger.info("Blog: Starte tägliche Artikel-Generierung...")

        # 1. Try RSS for fresh context
        rss_context = _fetch_rss_topics()

        # 2. Pick SEO topic
        topic = _pick_topic_from_schedule(app)

        # If RSS matched, blend context into topic but keep our SEO title
        if rss_context:
            logger.info(f"RSS-Kontext gefunden: {rss_context['source_title'][:60]}")

        # 3. Generate content
        body_html = _generate_article_with_openai(topic, rss_context)
        if not body_html:
            logger.warning("Blog: Artikel-Generierung fehlgeschlagen (kein OpenAI Inhalt)")
            return False

        # 4. Build slug (unique)
        base_slug = _slugify(topic["title"])
        slug = base_slug
        counter = 1
        while BlogPost.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        # 5. Meta description (first 155 chars of stripped text)
        stripped = re.sub(r'<[^>]+>', ' ', body_html)
        stripped = re.sub(r'\s+', ' ', stripped).strip()
        meta_description = stripped[:155].rsplit(' ', 1)[0] + '...' if len(stripped) > 155 else stripped

        now_iso = datetime.utcnow().isoformat()
        post_data = {
            "title": topic["title"],
            "slug": slug,
            "meta_description": meta_description,
            "meta_keywords": topic["main_keyword"] + ", " + ", ".join(topic.get("tags", [])),
            "body_html": body_html,
            "category": topic.get("category"),
            "tags": topic.get("tags", []),
            "source_url": rss_context["source_url"] if rss_context else None,
            "source_title": rss_context["source_title"] if rss_context else None,
            "read_time_minutes": _estimate_read_time(body_html),
            "is_published": True,
            "published_at": now_iso,
        }
        schema_markup = _build_schema_markup(post_data)

        post = BlogPost(
            title=post_data["title"],
            slug=slug,
            meta_description=meta_description,
            meta_keywords=post_data["meta_keywords"],
            body_html=body_html,
            category=topic.get("category"),
            source_url=post_data["source_url"],
            source_title=post_data["source_title"],
            read_time_minutes=post_data["read_time_minutes"],
            is_published=True,
            generated_at=datetime.utcnow(),
            published_at=datetime.utcnow(),
            schema_markup=schema_markup,
        )
        post.tags = topic.get("tags", [])

        db.session.add(post)
        db.session.commit()
        logger.info(f"Blog: Neuer Artikel veröffentlicht → /blog/{slug}")
        return True
