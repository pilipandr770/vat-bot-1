"""
Incident Response — BSI Meldung Draft Generator via Claude API.

Generates the three mandatory BSI notification stages:
  1. Frühwarnung (24h deadline)
  2. Zwischenmeldung (72h deadline)
  3. Abschlussbericht (30 days)
Plus DSGVO Art. 33 notification (72h to supervisory authority).
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

STAGE_META = {
    'fruehwarnung': {
        'label': 'Frühwarnung (24h)',
        'deadline_hours': 24,
        'bsi_form_id': 'Erstmeldung_NIS2',
        'description': (
            'Erste Benachrichtigung an das BSI innerhalb von 24 Stunden nach '
            'Kenntniserlangung eines erheblichen Sicherheitsvorfalls (§32 Abs. 2 BSIG).'
        ),
    },
    'zwischenmeldung': {
        'label': 'Zwischenmeldung (72h)',
        'deadline_hours': 72,
        'bsi_form_id': 'Zwischenmeldung_NIS2',
        'description': (
            'Erste Bewertung des Vorfalls inkl. Erstindikator für die Art des Vorfalls, '
            'Umfang und Auswirkungen — innerhalb von 72h (§32 Abs. 3 BSIG).'
        ),
    },
    'abschlussbericht': {
        'label': 'Abschlussbericht (30 Tage)',
        'deadline_hours': 30 * 24,
        'bsi_form_id': 'Abschlussbericht_NIS2',
        'description': (
            'Detaillierter Abschlussbericht mit Angaben zur Art der Bedrohung, '
            'ergriffenen Maßnahmen und grenzüberschreitenden Auswirkungen (§32 Abs. 4 BSIG).'
        ),
    },
    'dsgvo_art33': {
        'label': 'DSGVO Art. 33 (72h)',
        'deadline_hours': 72,
        'bsi_form_id': 'DSGVO_Art33_Meldung',
        'description': (
            'Meldung an die zuständige Datenschutz-Aufsichtsbehörde bei '
            'Datenschutzverletzungen (DSGVO Art. 33, 72h-Frist).'
        ),
    },
}

MODEL = 'claude-sonnet-4-6'


def generate_bsi_draft(stage: str, incident_data: dict) -> tuple[str, str | None]:
    """
    Generate a structured BSI notification draft using Claude AI.
    Returns (content_markdown, error_message).
    error_message is None on success.
    """
    prompt = _build_prompt(stage, incident_data)
    if not prompt:
        return '', f'Unbekannte Meldungsstufe: {stage}'

    try:
        import anthropic
        client = anthropic.Anthropic()
        message = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            messages=[
                {
                    'role': 'user',
                    'content': (
                        'Du bist ein NIS2-Compliance-Experte und hilfst einem Unternehmen dabei, '
                        'eine gesetzeskonforme BSI-Meldung nach §32 BSIG zu erstellen.\n\n'
                        + prompt
                    ),
                }
            ],
        )
        content = message.content[0].text if message.content else ''
        return content, None
    except Exception as exc:
        logger.error('Claude API error generating BSI draft %s: %s', stage, exc)
        return '', str(exc)


# ─────────────────────────────────────────────────────────────────
# Prompt builders per stage
# ─────────────────────────────────────────────────────────────────

def _build_prompt(stage: str, data: dict) -> str | None:
    builders = {
        'fruehwarnung': _prompt_fruehwarnung,
        'zwischenmeldung': _prompt_zwischenmeldung,
        'abschlussbericht': _prompt_abschlussbericht,
        'dsgvo_art33': _prompt_dsgvo_art33,
    }
    builder = builders.get(stage)
    return builder(data) if builder else None


def _prompt_fruehwarnung(d: dict) -> str:
    return f"""
Erstelle eine **BSI-Frühwarnung (Erstmeldung)** nach §32 Abs. 2 BSIG für folgenden Sicherheitsvorfall:

**Unternehmensdetails:**
- Unternehmen: {d.get('company_name', '[Name]')}
- Sektor: {d.get('sector', '[Sektor]')}
- Kontakt: {d.get('contact_name', '[Ansprechpartner]')}, {d.get('contact_email', '[E-Mail]')}

**Vorfallsdetails:**
- Titel: {d.get('title', '[Vorfallstitel]')}
- Erkennungszeitpunkt: {d.get('detected_at', '[Datum/Uhrzeit]')}
- Erster betroffener Zeitpunkt: {d.get('occurred_at', '[Datum/Uhrzeit]')}
- Kategorie: {d.get('category', '[Kategorie]')}
- Kurzbeschreibung: {d.get('description', '[Beschreibung]')}
- Betroffene Systeme: {d.get('affected_systems', '[Systeme]')}

Das Dokument soll folgende Struktur haben:
1. Meldekopf (Meldungsnummer, Datum/Uhrzeit der Meldung, BSI-Referenz)
2. Melder (Unternehmen, Ansprechpartner, Kontakt, NIS2-Einstufung)
3. Kurzbeschreibung des Vorfalls
4. Erste Einschätzung der Schwere (erheblich/nicht erheblich, Begründung)
5. Aktueller Status und erste Sofortmaßnahmen
6. Nächste Schritte und Meldung der Zwischenmeldung bis [72h-Deadline]

Stil: Sachlich, präzise, juristisch korrekt. Format: Markdown.
Hinweis: Dies ist eine Frühwarnung — nicht alle Details sind bekannt. Das soll explizit im Text stehen.
"""


def _prompt_zwischenmeldung(d: dict) -> str:
    return f"""
Erstelle eine **BSI-Zwischenmeldung** nach §32 Abs. 3 BSIG für den folgenden Sicherheitsvorfall:

**Unternehmensdetails:**
- Unternehmen: {d.get('company_name', '[Name]')}
- Sektor: {d.get('sector', '[Sektor]')}
- BSI-Referenz der Frühwarnung: {d.get('bsi_reference', '[BSI-Referenz]')}

**Vorfallsdetails:**
- Titel: {d.get('title', '[Titel]')}
- Erkennungszeitpunkt: {d.get('detected_at', '[Datum]')}
- Kategorie: {d.get('category', '[Kategorie]')}
- Beschreibung: {d.get('description', '[Beschreibung]')}
- Betroffene Systeme: {d.get('affected_systems', '[Systeme]')}
- Betroffene Personen/Daten: {d.get('affected_data', 'keine personenbezogenen Daten')}
- Ergriffene Maßnahmen bisher: {d.get('mitigation_steps', '[Maßnahmen]')}
- Aktueller Status: {d.get('current_status', '[Status]')}

Struktur:
1. Bezug auf die Frühwarnung
2. Aktualisierte Vorfallsbeschreibung und -einordnung
3. Technische Analyse (Angriffsvektor, Ausbreitung, betroffene Systeme)
4. Auswirkungsanalyse (Vertraulichkeit, Integrität, Verfügbarkeit)
5. Grenzüberschreitende Auswirkungen (ja/nein, Begründung)
6. Ergriffene Sofortmaßnahmen (chronologisch)
7. Weitere geplante Maßnahmen
8. Einschätzung: erheblicher Vorfall nach §31 Abs. 2 BSIG (Begründung)
9. Zeitplan Abschlussbericht

Format: Markdown. Sachlich, präzise, vollständig.
"""


def _prompt_abschlussbericht(d: dict) -> str:
    return f"""
Erstelle einen **BSI-Abschlussbericht** nach §32 Abs. 4 BSIG für den Sicherheitsvorfall:

**Unternehmensdetails:**
- Unternehmen: {d.get('company_name', '[Name]')}
- Sektor: {d.get('sector', '[Sektor]')}
- BSI-Referenz: {d.get('bsi_reference', '[Referenz]')}

**Vorfallsdetails:**
- Titel: {d.get('title', '[Titel]')}
- Zeitraum: {d.get('detected_at', '[Beginn]')} bis {d.get('resolved_at', '[Ende]')}
- Kategorie: {d.get('category', '[Kategorie]')}
- Vollständige Beschreibung: {d.get('description', '[Beschreibung]')}
- Root Cause: {d.get('root_cause', '[Ursache]')}
- Gesamtschaden / Auswirkungen: {d.get('impact_summary', '[Auswirkungen]')}
- Alle Maßnahmen: {d.get('all_measures', '[Maßnahmen]')}
- Präventivmaßnahmen: {d.get('prevention_measures', '[Prävention]')}

Struktur:
1. Zusammenfassung des Vorfalls
2. Chronologische Darstellung (Detection → Containment → Eradication → Recovery)
3. Technische Analyse
   - Angriffsvektor und Taktiken (MITRE ATT&CK-Referenz wenn möglich)
   - Betroffene Systeme, Daten, Dienste
   - Root Cause Analysis
4. Auswirkungsanalyse
   - Betriebliche Auswirkungen
   - Betroffene Kunden / Dritte
   - Grenzüberschreitende Auswirkungen (§32 Abs. 4 Nr. 2)
5. Alle ergriffenen Maßnahmen (chronologisch)
6. Lessons Learned und Empfehlungen
7. Implementierte Präventivmaßnahmen
8. Schlussfolgerung

Format: Markdown. Vollständig, sachlich, dokumentiert.
"""


def _prompt_dsgvo_art33(d: dict) -> str:
    return f"""
Erstelle eine **DSGVO Art. 33 Datenpannenmeldung** an die Datenschutz-Aufsichtsbehörde:

**Verantwortlicher:**
- Unternehmen: {d.get('company_name', '[Name]')}
- Adresse: {d.get('company_address', '[Adresse]')}
- DSB/Ansprechpartner: {d.get('dpo_contact', '[DSB-Kontakt]')}

**Datenpannensdetails:**
- Zeitpunkt der Datenpanne: {d.get('breach_at', '[Zeitpunkt]')}
- Zeitpunkt der Kenntnisnahme: {d.get('discovered_at', '[Zeitpunkt]')}
- Kategorie der Datenpanne: {d.get('breach_category', '[Kategorie]')}
- Betroffene Datenkategorien: {d.get('affected_data_categories', '[Kategorien]')}
- Anzahl betroffener Personen: {d.get('affected_persons_count', '[Anzahl]')}
- Beschreibung: {d.get('description', '[Beschreibung]')}
- Ergriffene Maßnahmen: {d.get('mitigation_steps', '[Maßnahmen]')}

Struktur (gemäß DSGVO Art. 33 Abs. 3):
1. Beschreibung der Art der Verletzung (Kategorie, ungefähre Zahl der betroffenen Personen/Datensätze)
2. Name und Kontaktdaten des DSB oder sonstigen Anlaufstelle
3. Beschreibung der voraussichtlichen Folgen der Verletzung
4. Beschreibung der ergriffenen oder vorgeschlagenen Maßnahmen
5. Einschätzung: Meldepflicht an Betroffene (Art. 34 DSGVO) — ja/nein mit Begründung
6. Begründung, falls Meldung nach 72h erfolgt

Adressat: {d.get('supervisory_authority', 'Zuständige Datenschutz-Aufsichtsbehörde (je nach Bundesland)')}
Format: Markdown, formelles Schreiben, juristisch korrekt.
"""
