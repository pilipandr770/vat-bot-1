"""
ISMS Document Generator — AI-powered via Claude API.

Generates all 10 mandatory NIS2/BSIG §30 policy documents
based on a 4-phase structured interview.
"""

import json
import logging
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
# Interview Phase Definitions
# Each phase is a list of questions with keys used in the answers dict
# ─────────────────────────────────────────────────────────────────

PHASES = {
    1: {
        'title': 'Unternehmensprofil',
        'subtitle': 'Grundlegende Informationen über Ihr Unternehmen',
        'icon': 'bi-building',
        'questions': [
            {
                'key': 'company_name',
                'label': 'Firmenname',
                'type': 'text',
                'required': True,
                'placeholder': 'Mustermann GmbH',
            },
            {
                'key': 'sector',
                'label': 'Branche / Sektor',
                'type': 'select',
                'required': True,
                'options': [
                    'IT-Dienstleistungen', 'Softwareentwicklung', 'Produktion / Fertigung',
                    'Energie & Versorgung', 'Gesundheitswesen', 'Logistik & Transport',
                    'Finanzdienstleistungen', 'Handel (B2B/B2C)', 'Beratung & Professional Services',
                    'Sonstiges',
                ],
            },
            {
                'key': 'employee_count',
                'label': 'Anzahl Mitarbeiter',
                'type': 'select',
                'required': True,
                'options': ['10–49', '50–99', '100–249', '250–499', '500–999', '≥1000'],
            },
            {
                'key': 'existing_certifications',
                'label': 'Vorhandene Zertifizierungen',
                'type': 'checkboxes',
                'required': False,
                'options': ['ISO 27001', 'ISO 9001', 'SOC 2', 'BSI IT-Grundschutz',
                            'TISAX', 'keine'],
            },
            {
                'key': 'compliance_goal',
                'label': 'Primäres Compliance-Ziel',
                'type': 'select',
                'required': True,
                'options': [
                    'NIS2-Pflichterfüllung (§30 BSIG)',
                    'Vorbereitung auf NIS2-Nachweis (§39 BSIG)',
                    'Auftrag eines Kunden / Lieferanten',
                    'Allgemeine Sicherheitsverbesserung',
                    'Versicherungsanforderung',
                ],
            },
        ],
    },
    2: {
        'title': 'IT-Infrastruktur',
        'subtitle': 'Überblick über Ihre technische Landschaft',
        'icon': 'bi-server',
        'questions': [
            {
                'key': 'infrastructure_type',
                'label': 'Art der IT-Infrastruktur',
                'type': 'select',
                'required': True,
                'options': ['Vollständig On-Premise', 'Überwiegend Cloud (IaaS/SaaS)',
                            'Hybrid (On-Prem + Cloud)', 'Co-Location Rechenzentrum'],
            },
            {
                'key': 'cloud_providers',
                'label': 'Verwendete Cloud-Anbieter',
                'type': 'checkboxes',
                'required': False,
                'options': ['AWS', 'Microsoft Azure', 'Google Cloud', 'Hetzner', 'IONOS',
                            'Microsoft 365 / Office 365', 'Google Workspace', 'keine'],
            },
            {
                'key': 'critical_systems',
                'label': 'Geschäftskritische Systeme (Freitext)',
                'type': 'textarea',
                'required': True,
                'placeholder': 'z.B. ERP (SAP), CRM (Salesforce), Warenwirtschaft, Webshop, Produktionssysteme...',
                'rows': 4,
            },
            {
                'key': 'external_service_providers',
                'label': 'Externe IT-Dienstleister',
                'type': 'textarea',
                'required': False,
                'placeholder': 'z.B. IT-Support durch XYZ GmbH, Hosting durch ABC AG...',
                'rows': 3,
            },
            {
                'key': 'remote_work',
                'label': 'Homeoffice / Remote Work',
                'type': 'select',
                'required': True,
                'options': ['Kein Remote Work', 'Weniger als 20% remote',
                            '20–50% remote', 'Mehr als 50% remote', 'Vollständig remote'],
            },
        ],
    },
    3: {
        'title': 'Bestehendes Sicherheitsniveau',
        'subtitle': 'Was ist bereits vorhanden?',
        'icon': 'bi-shield-half',
        'questions': [
            {
                'key': 'existing_measures',
                'label': 'Bereits implementierte Sicherheitsmaßnahmen',
                'type': 'checkboxes',
                'required': False,
                'options': [
                    'Firewall', 'Antivirus / EDR', 'MFA für Mitarbeiter',
                    'Passwort-Manager', 'VPN für Remote Access', 'Backup-System',
                    'Patch-Management-Prozess', 'Security Awareness Training',
                    'Incident Response Prozess', 'Netzwerksegmentierung',
                    'SIEM / Log-Management', 'Nichts davon',
                ],
            },
            {
                'key': 'backup_strategy',
                'label': 'Backup-Strategie',
                'type': 'select',
                'required': True,
                'options': [
                    'Kein systematisches Backup',
                    'Tägliches lokales Backup',
                    'Tägliches Backup + offsite Kopie',
                    '3-2-1-Backup-Strategie implementiert',
                    'Automatisiertes Backup mit regelmäßigem Restore-Test',
                ],
            },
            {
                'key': 'iam_solution',
                'label': 'Zugriffsmanagement (IAM)',
                'type': 'select',
                'required': True,
                'options': [
                    'Keine zentrale Verwaltung',
                    'Active Directory / LDAP',
                    'Azure AD / Entra ID',
                    'Google Workspace IAM',
                    'Dediziertes IAM-System (Okta, etc.)',
                ],
            },
            {
                'key': 'past_incidents',
                'label': 'Vergangene Sicherheitsvorfälle (letzten 3 Jahre)',
                'type': 'select',
                'required': True,
                'options': [
                    'Keine bekannten Vorfälle',
                    'Phishing-Angriffe (erfolgreich abgewehrt)',
                    'Phishing-Angriff mit Datenzugriff',
                    'Ransomware-Angriff',
                    'Datenverlust oder -diebstahl',
                    'Sonstiger Sicherheitsvorfall',
                ],
            },
        ],
    },
    4: {
        'title': 'Risikobewertung',
        'subtitle': 'Kritische Prozesse und Risikotoleranz',
        'icon': 'bi-exclamation-triangle',
        'questions': [
            {
                'key': 'rto_rpo',
                'label': 'Maximal tolerierbarer Ausfall kritischer Systeme (RTO)',
                'type': 'select',
                'required': True,
                'options': [
                    'Bis 1 Stunde (hochkritisch)',
                    '1–4 Stunden',
                    '4–24 Stunden',
                    '1–3 Tage',
                    'Mehr als 3 Tage',
                ],
            },
            {
                'key': 'data_categories',
                'label': 'Verarbeitete Datenkategorien',
                'type': 'checkboxes',
                'required': False,
                'options': [
                    'Personenbezogene Daten (DSGVO)',
                    'Gesundheitsdaten',
                    'Finanzdaten',
                    'Geschäftsgeheimnisse / IP',
                    'Kundendaten',
                    'Produktionsdaten / OT',
                    'Behördliche / regulatorische Daten',
                ],
            },
            {
                'key': 'biggest_risks',
                'label': 'Größte identifizierte Risiken für Ihr Unternehmen',
                'type': 'textarea',
                'required': False,
                'placeholder': 'z.B. Ransomware auf Produktionssysteme, Phishing gegen Buchhaltung, Ausfall des Warenwirtschaftssystems...',
                'rows': 3,
            },
            {
                'key': 'documents_to_generate',
                'label': 'Zu erstellende Dokumente (Pflichtauswahl)',
                'type': 'checkboxes',
                'required': True,
                'options': [
                    'security_policy|IT-Sicherheitsleitlinie (§30 Nr. 1)',
                    'risk_analysis|Risikoanalyse & Risikobewertung (§30 Nr. 1)',
                    'incident_response_plan|Incident Response Plan (§30 Nr. 2)',
                    'bcm_plan|Business Continuity Plan / BCP (§30 Nr. 3)',
                    'supply_chain_policy|Supply Chain Security Policy (§30 Nr. 4)',
                    'vulnerability_mgmt|Schwachstellenmanagement-Konzept (§30 Nr. 5)',
                    'crypto_concept|Kryptographie-Konzept (§30 Nr. 8)',
                    'access_control|Zugriffskontroll-Konzept / IAM (§30 Nr. 9)',
                    'mfa_communication|MFA & sichere Kommunikation (§30 Nr. 10)',
                    'training_concept|Schulungskonzept Cyber-Hygiene (§30 Nr. 7)',
                ],
                'select_all': True,
            },
        ],
    },
}


# ─────────────────────────────────────────────────────────────────
# Document Templates (prompts for Claude)
# ─────────────────────────────────────────────────────────────────

DOCUMENT_PROMPTS = {
    'security_policy': """
Du erstellst eine **IT-Sicherheitsleitlinie** nach BSI-Standard 200-1 für:

Unternehmen: {company_name}
Branche: {sector}
Größe: {employee_count} Mitarbeiter
IT-Infrastruktur: {infrastructure_type}
Cloud-Anbieter: {cloud_providers}
Existing measures: {existing_measures}

Die Leitlinie muss folgende Kapitel enthalten:
1. Präambel und Geltungsbereich
2. Sicherheitsziele und -strategie (ISMS-Scope)
3. Verantwortlichkeiten (Geschäftsleitung, IT-Leiter, alle Mitarbeiter)
4. Grundlegende Sicherheitsprinzipien (Vertraulichkeit, Integrität, Verfügbarkeit)
5. Klassifizierung von Informationen
6. Physische und logische Sicherheit
7. Umgang mit Sicherheitsvorfällen
8. Schulung und Sensibilisierung
9. Compliance und Überprüfung
10. Gültigkeitsdauer und Revisionshistorie

Anforderungen:
- Professionelle, formale Sprache auf Deutsch
- Unternehmensspezifisch (nutze die Angaben oben)
- Unterzeichnung durch Geschäftsleitung vorgesehen
- Revisionsintervall: 12 Monate
- NIS2-konform (§30 Abs. 2 Nr. 1 BSIG / NIS2UmsuCG)
- Format: Markdown mit klarer Kapitelstruktur

Erstelle ein vollständiges, sofort verwendbares Dokument.
""",

    'risk_analysis': """
Du erstellst eine **Risikoanalyse & Risikobewertung** nach BSI-Standard 200-3 für:

Unternehmen: {company_name}
Branche: {sector}
Kritische Systeme: {critical_systems}
RTO-Anforderung: {rto_rpo}
Daten-Kategorien: {data_categories}
Vergangene Vorfälle: {past_incidents}
Größte identifizierte Risiken: {biggest_risks}

Das Dokument muss enthalten:
1. Einleitung und Zweck
2. Methodik (BSI-Grundschutz-Ansatz)
3. Schutzbedarfsfeststellung
   - Kritische Geschäftsprozesse
   - Informationsklassen und Schutzbedarfskategorien (Normal / Hoch / Sehr Hoch)
4. Bedrohungsanalyse (Top-10 für den Sektor {sector})
5. Schwachstellenanalyse
6. Risikobewertungsmatrix (Wahrscheinlichkeit × Auswirkung)
7. Top-10-Risiken mit Bewertung und Maßnahmen
8. Restrisiken und Akzeptanzentscheidung
9. Überprüfungsintervall und Verantwortlichkeiten

Anforderungen: NIS2-konform (§30 Abs. 2 Nr. 1 BSIG), Markdown-Format, 
unternehmensspezifisch, professionelles Deutsch.
""",

    'incident_response_plan': """
Du erstellst einen **Incident Response Plan (IRP)** nach NIST SP 800-61 und BSI 100-4 für:

Unternehmen: {company_name}
Branche: {sector}
Kritische Systeme: {critical_systems}
IT-Infrastruktur: {infrastructure_type}
IAM-Lösung: {iam_solution}

Das Dokument muss enthalten:
1. Zweck und Geltungsbereich
2. Definitionen (Incident, Event, Breach)
3. Incident Response Team (IRT) — Rollen & Verantwortlichkeiten
4. Eskalationsmatrix (wer entscheidet was ab welchem Schweregrad)
5. Phase 1: Vorbereitung
   - Kontaktliste (BSI-CERT, externe Forensik, Rechtsanwalt, Versicherung)
   - Toolset und Kommunikationskanäle
6. Phase 2: Erkennung & Analyse
   - Incident-Klassifikation (Critical / High / Medium / Low)
   - Erste Beweissicherung
7. Phase 3: Eindämmung (Containment)
   - Sofortmaßnahmen je Incident-Typ (Ransomware, Phishing, Data Breach)
8. Phase 4: Beseitigung (Eradication)
9. Phase 5: Wiederherstellung (Recovery)
10. Phase 6: Nachbereitung (Lessons Learned)
11. **BSI-Meldepflicht §32 BSIG**: 
    - 24h Frühwarnung
    - 72h Zwischenmeldung  
    - 30 Tage Abschlussbericht
    - Meldeformular und Kontakt: BSI MUK-Portal
12. DSGVO Art. 33: 72h Meldepflicht bei Datenschutzverletzungen
13. Anhänge: Playbooks für häufige Vorfallstypen

Anforderungen: NIS2-konform (§30 Abs. 2 Nr. 2, §32 BSIG), Markdown, Deutsch, vollständig.
""",

    'bcm_plan': """
Du erstellst einen **Business Continuity Plan (BCP) & Disaster Recovery Plan (DRP)** nach BSI 100-4 für:

Unternehmen: {company_name}
Branche: {sector}
Kritische Systeme: {critical_systems}
RTO / maximaler Ausfall: {rto_rpo}
Backup-Strategie: {backup_strategy}
IT-Infrastruktur: {infrastructure_type}

Das Dokument muss enthalten:
1. Einleitung und Geltungsbereich
2. Geschäftsfortführungsstrategie
3. Business Impact Analysis (BIA)
   - Kritische Geschäftsprozesse mit RTO/RPO-Werten
   - Abhängigkeiten und Single Points of Failure
4. Krisenorganisation
   - Krisenstab-Zusammensetzung und Aktivierung
   - Kommunikationsplan (intern / extern / Medien)
5. Backup & Recovery-Konzept
   - Backup-Typen, -Frequenz, Aufbewahrungsfristen
   - Recovery-Prozeduren (schritt für Schritt)
   - Restore-Test-Protokoll (mindestens quartalsweise)
6. Notfallpläne je Szenario
   - Ausfall kritischer IT-Systeme
   - Ransomware / Cybervórfall
   - Ausfall Rechenzentrum / Cloud-Anbieter
   - Verlust wichtiger Mitarbeiter
7. Wiederanlaufplan (schrittweise Wiederherstellung)
8. Testkonzept (Tabletop-Übungen, technische Tests)
9. Plan-Wartung und Revisionshistorie

Anforderungen: NIS2-konform (§30 Abs. 2 Nr. 3 BSIG), Markdown, Deutsch, praxistauglich.
""",

    'supply_chain_policy': """
Du erstellst eine **Supply Chain Security Policy** nach §30 Abs. 2 Nr. 4 BSIG für:

Unternehmen: {company_name}
Branche: {sector}
Externe Dienstleister: {external_service_providers}

Das Dokument muss enthalten:
1. Geltungsbereich und Zielsetzung
2. Klassifikation von Lieferanten nach Kritikalität
3. Due-Diligence-Prozess bei Lieferantenauswahl
   - Sicherheitsfragebögen
   - Zertifizierungsprüfung (ISO 27001, SOC 2)
   - VAT- und Handelsregisterprüfung
4. Vertragliche Anforderungen an Lieferanten
   - Auftragsverarbeitungsvertrag (AVV, DSGVO Art. 28)
   - IT-Sicherheits-Klauseln
   - Meldepflichten des Lieferanten
5. Laufendes Lieferanten-Monitoring
   - Quartalsweise Überprüfung kritischer Lieferanten
   - Jahresbewertung aller Lieferanten
6. Maßnahmen bei Sicherheitsvorfällen beim Lieferanten
7. Offboarding und Datenlöschung bei Vertragsende
8. Verantwortlichkeiten und Revisionszyklus

Anforderungen: NIS2-konform (§30 Abs. 2 Nr. 4 BSIG), Markdown, Deutsch.
""",

    'vulnerability_mgmt': """
Du erstellst ein **Schwachstellenmanagement-Konzept** nach §30 Abs. 2 Nr. 5 BSIG für:

Unternehmen: {company_name}
Branche: {sector}
IT-Infrastruktur: {infrastructure_type}
Kritische Systeme: {critical_systems}

Das Dokument muss enthalten:
1. Zielsetzung und Geltungsbereich
2. Schwachstellen-Discovery
   - Regelmäßige Vulnerability Scans (intern + extern)
   - CVE-Monitoring (NVD, BSI CERT-Bund, Hersteller-Advisories)
   - Penetrationstests (Frequenz nach Kritikalität)
3. Risikobewertung und Priorisierung (CVSS-Score)
4. Patch-Management-Prozess
   - Kritische Patches: innerhalb 72h
   - Wichtige Patches: innerhalb 30 Tage
   - Normalpatches: innerhalb 90 Tage
   - Ausnahme-/Kompensationsmaßnahmen
5. Test- und Deployment-Prozess für Patches
6. Asset-Inventar als Grundlage (Scope)
7. Reporting und KPIs (Mean Time to Patch)
8. Verantwortlichkeiten, Tools, Revisionszyklus

Anforderungen: NIS2-konform (§30 Abs. 2 Nr. 5 BSIG), Markdown, Deutsch, detailliert.
""",

    'crypto_concept': """
Du erstellst ein **Kryptographie-Konzept** nach §30 Abs. 2 Nr. 8 BSIG und BSI TR-02102 für:

Unternehmen: {company_name}
Branche: {sector}
IT-Infrastruktur: {infrastructure_type}
Daten-Kategorien: {data_categories}

Das Dokument muss enthalten:
1. Geltungsbereich und Schutzziele
2. Kryptographische Anforderungen nach Datenkategorie
3. Zulässige Algorithmen und Schlüssellängen
   - Symmetrisch: AES-256
   - Asymmetrisch: RSA-4096 oder ECDSA-384
   - Hashfunktionen: SHA-256 oder besser
   - Grundlage: BSI TR-02102-1 (aktuelle Version)
4. Transport-Verschlüsselung
   - TLS 1.2 / 1.3 (nur TLS 1.3 für neue Systeme)
   - Zertifikats-Management (CA, Lebensdauer, Renewal)
   - E-Mail-Verschlüsselung (S/MIME oder PGP)
5. Ruhende Daten (Data at Rest)
   - Festplattenverschlüsselung (BitLocker / dm-crypt)
   - Datenbankfeld-Verschlüsselung für sensitive Daten
   - Backup-Verschlüsselung
6. Schlüsselmanagement
   - Schlüsselerzeugung, -speicherung (HSM oder sicherer Store)
   - Schlüsselrotation und -archivierung
   - Zugriffskontrolle auf Schlüssel
7. Kryptographie-Verbote (schwache Algorithmen: MD5, SHA-1, DES, RC4)
8. Überprüfung und Aktualisierung

Anforderungen: NIS2-konform (§30 Abs. 2 Nr. 8 BSIG), BSI TR-02102, Markdown, Deutsch.
""",

    'access_control': """
Du erstellst ein **Zugriffskontroll-Konzept (IAM)** nach §30 Abs. 2 Nr. 9 BSIG für:

Unternehmen: {company_name}
Branche: {sector}
IAM-Lösung: {iam_solution}
Mitarbeiterzahl: {employee_count}
Remote Work: {remote_work}

Das Dokument muss enthalten:
1. Geltungsbereich und Grundsätze (Need-to-Know, Least Privilege, Separation of Duties)
2. Benutzerkonten-Management
   - Onboarding-Prozess (Antragsformular, Genehmigung, Einrichtung)
   - Passwort-Richtlinien (Länge ≥12, Komplexität, Rotation)
   - Privileged Access Management (PAM)
3. Rollenbasierte Zugriffskontrolle (RBAC)
   - Rollen-Definitionen für typische Positionen
   - Berechtigungsmatrix
4. Multi-Faktor-Authentifizierung
   - Pflicht für: Remote Access, Admin-Konten, Cloud-Dienste, E-Mail
   - Empfohlene MFA-Methoden (TOTP, FIDO2/WebAuthn)
5. Privilegierte Konten (Admin-Accounts)
   - Separate Admin-Konten, kein Internetzugang
   - Just-in-Time Access für hochprivilegierte Operationen
6. Offboarding-Prozess
   - Sofortige Sperrung bei Austritt
   - Archivierung von Daten, Rückgabe von Geräten
7. Regelmäßige Zugriffsüberprüfung (min. jährlich)
8. Asset-Inventar: Systeme und Dienste mit Zugriffsrechten

Anforderungen: NIS2-konform (§30 Abs. 2 Nr. 9 BSIG), Markdown, Deutsch, vollständig.
""",

    'mfa_communication': """
Du erstellst eine **MFA & sichere Kommunikation Policy** nach §30 Abs. 2 Nr. 10 BSIG für:

Unternehmen: {company_name}
Branche: {sector}
Remote Work: {remote_work}
IT-Infrastruktur: {infrastructure_type}

Das Dokument muss enthalten:
1. Geltungsbereich und Zielsetzung
2. Multi-Faktor-Authentifizierung (MFA)
   - Anwendungsbereich (welche Systeme/Dienste sind betroffen)
   - Pflicht-MFA: Remote Access VPN, Cloud-Admin, E-Mail-Zugang, kritische Anwendungen
   - Empfohlene MFA-Methoden: FIDO2/WebAuthn (Präferenz), TOTP, SMS (nur wenn notwendig)
   - Notfall-Zugangsprozedur (wenn MFA-Gerät verloren)
3. Sichere E-Mail-Kommunikation
   - Verschlüsselung (S/MIME, PGP) für sensitive Kommunikation
   - Digitale Signaturen
   - Umgang mit verdächtigen E-Mails
4. Sichere Sprach- / Videokommunikation
   - Genehmigte Plattformen für vertrauliche Calls (Teams, Webex)
   - Verbotene Plattformen für Geschäftsgeheimnisse
5. Messaging und Collaboration
   - Genehmigte Tools (intern + extern)
   - Dateiübertragung (sichere Alternativen zu unsicheren Methoden)
6. Notfallkommunikation (Out-of-Band Channel)
   - Alternativer Kommunikationskanal bei IT-Ausfall
   - Notfallkontaktliste (offline verfügbar)
7. Kryptographische Anforderungen an Kommunikationssysteme

Anforderungen: NIS2-konform (§30 Abs. 2 Nr. 10 BSIG), Markdown, Deutsch.
""",

    'training_concept': """
Du erstellst ein **Schulungskonzept Cyber-Hygiene & Security Awareness** nach §30 Abs. 2 Nr. 7 BSIG für:

Unternehmen: {company_name}
Branche: {sector}
Mitarbeiterzahl: {employee_count}
Vergangene Vorfälle: {past_incidents}

Das Dokument muss enthalten:
1. Geltungsbereich und gesetzliche Grundlage (§30 Nr. 7 BSIG, §38 BSIG)
2. Zielgruppen und spezifische Schulungsanforderungen
   - Alle Mitarbeiter: Basis-Awareness (jährlich)
   - IT-Personal: Technische Schulungen (halbjährlich)
   - Geschäftsleitung: §38-BSIG-Schulung (alle 3 Jahre)
3. Schulungsthemen Jahresplan
   - Monat 1: Passwortsicherheit & MFA
   - Monat 2: Phishing erkennen & melden
   - Monat 3: Social Engineering
   - Monat 4: DSGVO & Datenschutz am Arbeitsplatz
   - Monat 5: Ransomware & Incident Response
   - Monat 6: Mobile Sicherheit
   - (weitere 6 Themen für die zweite Jahreshälfte)
4. Phishing-Simulationstests (min. quartalsweise)
   - Planung und Durchführung
   - Nachschulungsprotokoll bei Klick
5. Nachweis und Dokumentation (BSI-konformer Nachweis für §39 BSIG)
   - Teilnahmebestätigungen
   - Testergebnisse
   - Schulungsregister
6. Verantwortlichkeiten, Budget, Revisionszyklus

Anforderungen: NIS2-konform (§30 Abs. 2 Nr. 7, §38 BSIG), Markdown, Deutsch, vollständig.
""",
}


class ISMSDocumentGenerator:
    """
    Generates ISMS policy documents using Claude AI.
    Takes structured interview data and returns Markdown content.
    """

    MODEL = 'claude-sonnet-4-6'

    def generate_document(self, doc_type: str, interview_data: dict) -> tuple[str, Optional[str]]:
        """
        Generate a single document.
        Returns (content_markdown, error_message).
        error_message is None on success.
        """
        prompt_template = DOCUMENT_PROMPTS.get(doc_type)
        if not prompt_template:
            return '', f'Unbekannter Dokumenttyp: {doc_type}'

        # Build a flat dict of all interview answers for formatting
        context = _flatten_interview_data(interview_data)

        try:
            prompt = prompt_template.format_map(_SafeDict(context))
        except Exception as exc:
            logger.warning('Prompt formatting error for %s: %s', doc_type, exc)
            prompt = prompt_template  # use template as-is

        try:
            import anthropic
            client = anthropic.Anthropic()
            message = client.messages.create(
                model=self.MODEL,
                max_tokens=4096,
                messages=[
                    {
                        'role': 'user',
                        'content': (
                            'Du bist ein erfahrener ISMS-Berater und Compliance-Experte '
                            'mit Spezialisierung auf NIS2UmsuCG und BSI-Standards.\n\n'
                            + prompt
                        ),
                    }
                ],
            )
            content = message.content[0].text if message.content else ''
            return content, None

        except Exception as exc:
            logger.error('Claude API error generating %s: %s', doc_type, exc)
            return '', str(exc)


def _flatten_interview_data(interview_data: dict) -> dict:
    """Flatten nested interview data into a single dict for prompt formatting."""
    flat = {}
    for phase_data in interview_data.values() if isinstance(interview_data, dict) else [interview_data]:
        if isinstance(phase_data, dict):
            for k, v in phase_data.items():
                if isinstance(v, list):
                    flat[k] = ', '.join(str(i) for i in v) if v else 'keine'
                elif v is not None:
                    flat[k] = str(v)
                else:
                    flat[k] = 'nicht angegeben'
        flat.update(phase_data if isinstance(phase_data, dict) else {})
    # Ensure required keys have defaults
    defaults = {
        'company_name': 'Ihr Unternehmen',
        'sector': 'nicht angegeben',
        'employee_count': 'nicht angegeben',
        'infrastructure_type': 'nicht angegeben',
        'cloud_providers': 'keine',
        'critical_systems': 'nicht angegeben',
        'external_service_providers': 'keine',
        'remote_work': 'nicht angegeben',
        'existing_measures': 'keine',
        'backup_strategy': 'nicht angegeben',
        'iam_solution': 'nicht angegeben',
        'past_incidents': 'keine bekannten Vorfälle',
        'rto_rpo': 'nicht angegeben',
        'data_categories': 'nicht angegeben',
        'biggest_risks': 'nicht angegeben',
    }
    for k, v in defaults.items():
        flat.setdefault(k, v)
    return flat


class _SafeDict(dict):
    """dict subclass that returns '{key}' for missing keys instead of raising KeyError."""
    def __missing__(self, key):
        return f'{{{key}}}'


def get_phase_definitions():
    """Return phase definitions for use in templates."""
    return PHASES
