"""
NIS2 Compliance Platform — Database Models

All NIS2-related tables prefixed with 'nis2_'.
Uses same db instance as the rest of the application.

Tables:
  BSI Registration:
    nis2_bsi_registrations

  Continuous Monitoring:
    nis2_monitoring_targets
    nis2_monitoring_scans

  ISMS Documents:
    nis2_isms_interviews
    nis2_isms_documents

  Incident Response:
    nis2_incidents
    nis2_incident_drafts
    nis2_incident_timeline

  Supply Chain:
    nis2_suppliers
    nis2_supplier_assessments
"""

import os
import json
from datetime import datetime, date

from crm.models import db

SCHEMA = os.environ.get('DB_SCHEMA') or None
_sp = f'{SCHEMA}.' if SCHEMA else ''


# ─────────────────────────────────────────────────────────────────
# BSI REGISTRATION
# ─────────────────────────────────────────────────────────────────

# Structured sector groups for <optgroup> rendering in templates.
# Each entry: (group_label, [(value, label), ...])
NIS2_SECTOR_GROUPS = [
    ('⚡ Energie (Anlage 1 BSIG)', [
        ('energie_strom',       'Strom / Elektrizitätsversorgung'),
        ('energie_gas',         'Gas / Erdgas-Fernleitungen und -Verteilung'),
        ('energie_oel',         'Öl / Mineralöl-Versorgung und -Speicherung'),
        ('energie_fernwaerme',  'Fernwärme / Fernkälte'),
        ('energie_wasserstoff', 'Wasserstoff-Erzeugung, -Speicherung, -Transport'),
    ]),
    ('🚂 Transport & Verkehr (Anlage 1)', [
        ('transport_luftfahrt', 'Luftfahrt (Fluggesellschaften, Flughäfen, Flugsicherung)'),
        ('transport_bahn',      'Eisenbahn / Schienenverkehr'),
        ('transport_schiff',    'Schifffahrt / Hafenbetrieb / Schiffsmanagement'),
        ('transport_strasse',   'Straßenverkehr / Logistik / Lkw-Transporte'),
        ('transport_urban',     'Öffentlicher Nahverkehr (ÖPNV)'),
    ]),
    ('🏥 Gesundheitswesen (Anlage 1)', [
        ('gesundheit_krankenhaus',  'Krankenhäuser / Kliniken / stationäre Versorgung'),
        ('gesundheit_labor',        'Laboratorien / Diagnostik / Medizinlabore'),
        ('gesundheit_pharma',       'Pharmaindustrie / Arzneimittelherstellung'),
        ('gesundheit_medizingeraete','Medizingeräte-Hersteller (Klasse IIa/IIb/III)'),
        ('gesundheit_forschung',    'Medizinische Forschung / klinische Studien'),
    ]),
    ('💧 Wasser (Anlage 1)', [
        ('trinkwasser', 'Trinkwasser / Wasserversorgung und -aufbereitung'),
        ('abwasser',    'Abwasser / Abwasserentsorgung und -behandlung'),
    ]),
    ('🏦 Finanz & Banken (Anlage 1)', [
        ('bankwesen',    'Bankwesen / Kreditinstitute / Zahlungsdienstleister'),
        ('finanzmarkt',  'Finanzmarktinfrastrukturen (Börsen, CCPs, Handelsplätze)'),
    ]),
    ('💻 Digitale Infrastruktur & IT (Anlage 1)', [
        ('digital_cloud',    'Cloud Computing / SaaS / IaaS / PaaS'),
        ('digital_rz',       'Rechenzentren / Colocation-Betreiber'),
        ('digital_cdn',      'CDN / Content-Delivery-Netzwerke'),
        ('digital_dns',      'DNS-Auflösungsdienste / TLD-Registry'),
        ('digital_vertrauen','Qualifizierte Vertrauensdienste (eIDAS / eID)'),
        ('digital_telekom',  'Telekommunikation / Internet-Austauschpunkte (IXP)'),
        ('digital_netz',     'Öffentliche Kommunikationsnetze / ISP'),
        ('ikt_management',   'IKT-Dienstemanagement / Managed Service Provider (MSP)'),
    ]),
    ('🏛️ Öffentliche Verwaltung & Weltraum (Anlage 1)', [
        ('oeffentliche_verwaltung', 'Öffentliche Verwaltung (Bund, Länder, Kommunen)'),
        ('weltraum',                'Weltraum / Satellitenbetrieb / Bodenstationen'),
    ]),
    ('📦 Wichtige Einrichtungen — Anlage 2 BSIG', [
        ('post',                        'Post- und Kurierdienste'),
        ('abfallwirtschaft',            'Abfallwirtschaft / Entsorgung'),
        ('chemie',                      'Chemie / Herstellung und Vertrieb von Chemikalien'),
        ('lebensmittel',                'Lebensmittel / Produktion, Verarbeitung und Vertrieb'),
        ('verarbeitendes_medizin',      'Verarbeitendes Gewerbe — Medizingeräte (Klasse I)'),
        ('verarbeitendes_elektronik',   'Verarbeitendes Gewerbe — Computer / Elektronik / Optik'),
        ('verarbeitendes_maschinenbau', 'Verarbeitendes Gewerbe — Maschinenbau'),
        ('verarbeitendes_fahrzeuge',    'Verarbeitendes Gewerbe — Fahrzeugbau / Automotive'),
        ('verarbeitendes_gewerbe',      'Verarbeitendes Gewerbe — Sonstige Herstellung'),
        ('digitale_dienste_marktplatz', 'Digitale Dienste — Online-Marktplätze'),
        ('digitale_dienste_suche',      'Digitale Dienste — Online-Suchmaschinen'),
        ('digitale_dienste_sozial',     'Digitale Dienste — Soziale Netzwerke'),
        ('forschung',                   'Forschungseinrichtungen'),
    ]),
]

# Flat list (value, label) — kept for backward compatibility
NIS2_SECTORS = [
    (value, label)
    for _group_label, entries in NIS2_SECTOR_GROUPS
    for value, label in entries
]

LEGAL_FORMS = [
    'GmbH', 'AG', 'UG (haftungsbeschränkt)', 'OHG', 'KG', 'GmbH & Co. KG',
    'e.K.', 'GbR', 'Einzelunternehmen', 'Verein', 'Stiftung', 'Sonstige',
]


class BSIRegistration(db.Model):
    """BSI-MUK-Portal Registrierungsdaten für §33 BSIG."""

    __tablename__ = 'nis2_bsi_registrations'
    __table_args__ = {'schema': SCHEMA} if SCHEMA else {}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}users.id', ondelete='CASCADE'),
                        nullable=False, index=True)

    # ── Schritt 1: Unternehmensdaten ──────────────────────────────
    company_name = db.Column(db.String(300), nullable=False)
    legal_form = db.Column(db.String(50))
    hrb_number = db.Column(db.String(50))
    registry_court = db.Column(db.String(100))
    vat_id = db.Column(db.String(30))
    street = db.Column(db.String(200))
    postal_code = db.Column(db.String(10))
    city = db.Column(db.String(100))
    employee_count = db.Column(db.Integer)
    annual_revenue_eur = db.Column(db.BigInteger)

    # ── Schritt 2: Sektor & Klassifizierung ──────────────────────
    sector = db.Column(db.String(50))
    subsector = db.Column(db.String(100))
    # besonders_wichtig | wichtig | nicht_betroffen
    entity_type = db.Column(db.String(30))
    is_affected = db.Column(db.Boolean)

    # ── Schritt 3: Kontaktpersonen (JSON) ────────────────────────
    # {gf: {name, email, phone}, it_security: {…}, meldestelle: {…}}
    contacts_json = db.Column(db.Text)

    # ── Schritt 4: Technische Angaben (JSON) ─────────────────────
    # {ip_ranges: [], domains: [], cloud_providers: [], it_services: []}
    technical_json = db.Column(db.Text)

    # ── Status ───────────────────────────────────────────────────
    wizard_step = db.Column(db.Integer, default=1)
    is_complete = db.Column(db.Boolean, default=False)
    exported_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    def get_contacts(self):
        try:
            return json.loads(self.contacts_json) if self.contacts_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def get_technical(self):
        try:
            return json.loads(self.technical_json) if self.technical_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @property
    def entity_type_label(self):
        labels = {
            'besonders_wichtig': 'Besonders wichtige Einrichtung (bis €10 Mio / 2% Umsatz)',
            'wichtig': 'Wichtige Einrichtung (bis €7 Mio / 1,4% Umsatz)',
            'nicht_betroffen': 'Nicht betroffen von NIS2',
        }
        return labels.get(self.entity_type, 'Unbekannt')

    def __repr__(self):
        return f'<BSIRegistration {self.company_name} step={self.wizard_step}>'


# ─────────────────────────────────────────────────────────────────
# CONTINUOUS MONITORING
# ─────────────────────────────────────────────────────────────────

class MonitoringTarget(db.Model):
    """Domain/URL für automatisches Security-Monitoring."""

    __tablename__ = 'nis2_monitoring_targets'
    __table_args__ = {'schema': SCHEMA} if SCHEMA else {}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}users.id', ondelete='CASCADE'),
                        nullable=False, index=True)

    domain = db.Column(db.String(255), nullable=False)
    label = db.Column(db.String(100))                       # e.g. "Hauptwebsite", "Kundenportal"
    is_active = db.Column(db.Boolean, default=True)

    # monthly | weekly | quarterly
    scan_frequency = db.Column(db.String(20), default='monthly')
    last_scan_at = db.Column(db.DateTime)
    next_scan_at = db.Column(db.DateTime)
    last_score = db.Column(db.Float)
    previous_score = db.Column(db.Float)

    # Alert settings
    alert_on_degradation = db.Column(db.Boolean, default=True)
    alert_threshold = db.Column(db.Float, default=10.0)    # alert if score drops by this much
    alert_email = db.Column(db.String(200))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    scans = db.relationship('MonitoringScan', backref='target', lazy='dynamic',
                            cascade='all, delete-orphan',
                            order_by='MonitoringScan.scanned_at.desc()')

    @property
    def score_trend(self):
        """Returns 'up', 'down', or 'stable'."""
        if self.last_score is None or self.previous_score is None:
            return 'stable'
        diff = self.last_score - self.previous_score
        if diff >= 5:
            return 'up'
        if diff <= -5:
            return 'down'
        return 'stable'

    @property
    def score_color(self):
        if self.last_score is None:
            return 'secondary'
        if self.last_score >= 80:
            return 'success'
        if self.last_score >= 60:
            return 'warning'
        return 'danger'

    def __repr__(self):
        return f'<MonitoringTarget {self.domain}>'


class MonitoringScan(db.Model):
    """Einzelnes Scan-Ergebnis für ein Monitoring-Target."""

    __tablename__ = 'nis2_monitoring_scans'
    __table_args__ = {'schema': SCHEMA} if SCHEMA else {}

    id = db.Column(db.Integer, primary_key=True)
    target_id = db.Column(db.Integer,
                          db.ForeignKey(f'{_sp}nis2_monitoring_targets.id', ondelete='CASCADE'),
                          nullable=False, index=True)

    scan_type = db.Column(db.String(20), default='full')    # full | quick | headers_only
    score = db.Column(db.Float)
    results_json = db.Column(db.Text)                       # Full scan results
    diff_json = db.Column(db.Text)                          # Diff vs previous scan

    # Finding counts
    findings_count = db.Column(db.Integer, default=0)
    critical_count = db.Column(db.Integer, default=0)
    high_count = db.Column(db.Integer, default=0)
    medium_count = db.Column(db.Integer, default=0)
    low_count = db.Column(db.Integer, default=0)

    # Status
    triggered_by = db.Column(db.String(20), default='scheduler')  # scheduler | manual
    error_message = db.Column(db.Text)

    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_results(self):
        try:
            return json.loads(self.results_json) if self.results_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def get_diff(self):
        try:
            return json.loads(self.diff_json) if self.diff_json else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @property
    def score_color(self):
        if self.score is None:
            return 'secondary'
        if self.score >= 80:
            return 'success'
        if self.score >= 60:
            return 'warning'
        return 'danger'

    def __repr__(self):
        return f'<MonitoringScan target={self.target_id} score={self.score}>'


# ─────────────────────────────────────────────────────────────────
# ISMS DOCUMENTS
# ─────────────────────────────────────────────────────────────────

ISMS_DOC_TYPES = [
    ('security_policy',       'IT-Sicherheitsleitlinie',           '§30 Nr. 1', 'BSI 200-1'),
    ('risk_analysis',         'Risikoanalyse & Risikobewertung',   '§30 Nr. 1', 'BSI 200-3'),
    ('incident_response_plan','Incident Response Plan (IRP)',       '§30 Nr. 2', 'BSI 100-4'),
    ('bcm_plan',              'Business Continuity Plan (BCP/DRP)','§30 Nr. 3', 'BSI 100-4'),
    ('supply_chain_policy',   'Supply Chain Security Policy',      '§30 Nr. 4', 'BSI 200-1'),
    ('vulnerability_mgmt',    'Schwachstellenmanagement-Konzept',  '§30 Nr. 5', 'BSI 200-2'),
    ('crypto_concept',        'Kryptographie-Konzept',             '§30 Nr. 8', 'BSI 200-2'),
    ('access_control',        'Zugriffskontroll-Konzept (IAM)',    '§30 Nr. 9', 'BSI 200-2'),
    ('mfa_communication',     'MFA & sichere Kommunikation',       '§30 Nr. 10','BSI 200-2'),
    ('training_concept',      'Schulungskonzept Cyber-Hygiene',    '§30 Nr. 7', 'BSI 200-2'),
]

ISMS_DOC_TYPES_MAP = {t[0]: {'title': t[1], 'paragraph': t[2], 'bsi_std': t[3]}
                      for t in ISMS_DOC_TYPES}


class ISMSInterview(db.Model):
    """AI-gesteuertes Onboarding-Interview zur ISMS-Dokumentenerstellung."""

    __tablename__ = 'nis2_isms_interviews'
    __table_args__ = {'schema': SCHEMA} if SCHEMA else {}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}users.id', ondelete='CASCADE'),
                        nullable=False, index=True)

    # Quick-display name (extracted from Phase 1 data)
    company_name = db.Column(db.String(300))

    # Phases 1-4 (JSON per phase)
    company_profile_json = db.Column(db.Text)     # Phase 1
    it_landscape_json = db.Column(db.Text)        # Phase 2
    security_level_json = db.Column(db.Text)      # Phase 3
    risk_assessment_json = db.Column(db.Text)     # Phase 4

    current_phase = db.Column(db.Integer, default=1)
    is_complete = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)

    # Which documents to generate (JSON list of doc_type strings)
    requested_docs_json = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = db.relationship('ISMSDocument', backref='interview', lazy='dynamic',
                                cascade='all, delete-orphan')

    def get_phase_data(self, phase: int):
        field_map = {
            1: self.company_profile_json,
            2: self.it_landscape_json,
            3: self.security_level_json,
            4: self.risk_assessment_json,
        }
        raw = field_map.get(phase)
        try:
            return json.loads(raw) if raw else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_phase_data(self, phase: int, data: dict):
        serialized = json.dumps(data, ensure_ascii=False)
        if phase == 1:
            self.company_profile_json = serialized
        elif phase == 2:
            self.it_landscape_json = serialized
        elif phase == 3:
            self.security_level_json = serialized
        elif phase == 4:
            self.risk_assessment_json = serialized

    def get_all_data(self):
        result = {}
        for phase in range(1, 5):
            result.update(self.get_phase_data(phase))
        return result

    def __repr__(self):
        return f'<ISMSInterview user={self.user_id} phase={self.current_phase}>'


class ISMSDocument(db.Model):
    """Generiertes ISMS-Dokument (10 Kernpolicies)."""

    __tablename__ = 'nis2_isms_documents'
    __table_args__ = {'schema': SCHEMA} if SCHEMA else {}

    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer,
                             db.ForeignKey(f'{_sp}nis2_isms_interviews.id', ondelete='CASCADE'),
                             nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}users.id', ondelete='CASCADE'),
                        nullable=False, index=True)

    doc_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(300))
    content_md = db.Column(db.Text)                      # Markdown content
    content = db.Column(db.Text)                         # Alias / generated content
    version = db.Column(db.Integer, default=1)
    bsi_standard_ref = db.Column(db.String(30))
    nis2_paragraph_ref = db.Column(db.String(30))

    # Generation status
    is_generated = db.Column(db.Boolean, default=False)
    generation_error = db.Column(db.Text)

    # Revision tracking
    next_review_date = db.Column(db.Date)
    last_reviewed_at = db.Column(db.DateTime)
    review_interval_months = db.Column(db.Integer, default=12)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def type_info(self):
        return ISMS_DOC_TYPES_MAP.get(self.doc_type, {})

    @property
    def review_overdue(self):
        if not self.next_review_date:
            return False
        return date.today() > self.next_review_date

    def __repr__(self):
        return f'<ISMSDocument {self.doc_type} v{self.version}>'


# ─────────────────────────────────────────────────────────────────
# INCIDENT RESPONSE
# ─────────────────────────────────────────────────────────────────

INCIDENT_CATEGORIES = [
    ('ransomware', 'Ransomware / Erpressung'),
    ('phishing', 'Phishing / Business Email Compromise'),
    ('data_breach', 'Datenschutzverletzung'),
    ('dos_ddos', 'DoS / DDoS-Angriff'),
    ('unauthorized_access', 'Unbefugter Zugriff'),
    ('malware', 'Malware / Schadsoftware'),
    ('insider_threat', 'Insider-Bedrohung'),
    ('supply_chain_attack', 'Lieferketten-Angriff'),
    ('vulnerability_exploit', 'Ausnutzung einer Schwachstelle'),
    ('other', 'Sonstiger Vorfall'),
]

INCIDENT_SEVERITIES = [
    ('critical', 'Kritisch — Betrieb vollständig ausgefallen'),
    ('high', 'Hoch — Betrieb stark beeinträchtigt'),
    ('medium', 'Mittel — Teilweise Beeinträchtigung'),
    ('low', 'Niedrig — Geringfügige Auswirkung'),
]


class Incident(db.Model):
    """IT-Sicherheitsvorfall (§30 Nr. 2, §32 BSIG)."""

    __tablename__ = 'nis2_incidents'
    __table_args__ = {'schema': SCHEMA} if SCHEMA else {}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}users.id', ondelete='CASCADE'),
                        nullable=False, index=True)

    incident_ref = db.Column(db.String(30), unique=True)   # INC-2026-XXXX

    # Core data
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default='medium')
    # open | contained | eradicated | recovered | closed
    status = db.Column(db.String(20), default='open', index=True)
    category = db.Column(db.String(50))

    # Affected systems / data (plaintext for quick entry)
    affected_systems = db.Column(db.Text)
    affected_data = db.Column(db.Text)
    affected_systems_json = db.Column(db.Text)             # JSON list (structured)
    affected_data_categories_json = db.Column(db.Text)     # JSON list

    # Investigation fields
    mitigation_steps = db.Column(db.Text)
    root_cause = db.Column(db.Text)
    impact_summary = db.Column(db.Text)

    # Timeline
    occurred_at = db.Column(db.DateTime)                   # when incident started
    detected_at = db.Column(db.DateTime, nullable=False)
    reported_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)                   # general resolved timestamp
    contained_at = db.Column(db.DateTime)
    eradicated_at = db.Column(db.DateTime)
    recovered_at = db.Column(db.DateTime)
    closed_at = db.Column(db.DateTime)

    # BSI Meldepflicht deadlines (§32 BSIG)
    fruehwarnung_deadline = db.Column(db.DateTime)         # detected_at + 24h
    zwischenmeldung_deadline = db.Column(db.DateTime)      # detected_at + 72h
    abschlussbericht_deadline = db.Column(db.DateTime)     # detected_at + 30 days

    fruehwarnung_sent = db.Column(db.Boolean, default=False)
    zwischenmeldung_sent = db.Column(db.Boolean, default=False)
    abschlussbericht_sent = db.Column(db.Boolean, default=False)

    # DSGVO Art. 33
    dsgvo_relevant = db.Column(db.Boolean, default=False)
    dpa_notification_required = db.Column(db.Boolean, default=False)
    dpa_notification_sent = db.Column(db.Boolean, default=False)
    dpa_notification_deadline = db.Column(db.DateTime)    # detected_at + 72h

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    drafts = db.relationship('IncidentDraft', backref='incident', lazy='dynamic',
                             cascade='all, delete-orphan',
                             order_by='IncidentDraft.created_at.desc()')
    timeline = db.relationship('IncidentTimeline', backref='incident', lazy='dynamic',
                               cascade='all, delete-orphan',
                               order_by='IncidentTimeline.timestamp.asc()')

    def get_affected_systems(self):
        try:
            return json.loads(self.affected_systems_json) if self.affected_systems_json else []
        except (json.JSONDecodeError, TypeError):
            return []

    def get_affected_data(self):
        try:
            return json.loads(self.affected_data_categories_json) if self.affected_data_categories_json else []
        except (json.JSONDecodeError, TypeError):
            return []

    @property
    def severity_color(self):
        return {'critical': 'danger', 'high': 'warning',
                'medium': 'info', 'low': 'secondary'}.get(self.severity, 'secondary')

    @property
    def status_color(self):
        return {'open': 'danger', 'contained': 'warning',
                'eradicated': 'info', 'recovered': 'success',
                'closed': 'secondary'}.get(self.status, 'secondary')

    @property
    def hours_since_detection(self):
        if not self.detected_at:
            return 0
        return int((datetime.utcnow() - self.detected_at).total_seconds() / 3600)

    def log(self, action: str, details: str = '', performed_by: str = 'system'):
        """Add an entry to the incident timeline."""
        entry = IncidentTimeline(
            incident_id=self.id,
            action=action,
            details=details,
            performed_by=performed_by,
        )
        db.session.add(entry)

    def __repr__(self):
        return f'<Incident {self.incident_ref} [{self.status}]>'


class IncidentDraft(db.Model):
    """Entwurf einer BSI-Meldung (Frühwarnung / Zwischenmeldung / Abschlussbericht)."""

    __tablename__ = 'nis2_incident_drafts'
    __table_args__ = {'schema': SCHEMA} if SCHEMA else {}

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer,
                            db.ForeignKey(f'{_sp}nis2_incidents.id', ondelete='CASCADE'),
                            nullable=False, index=True)

    # fruehwarnung | zwischenmeldung | abschlussbericht | dsgvo_art33
    stage = db.Column(db.String(30), nullable=False)
    content = db.Column(db.Text)
    version = db.Column(db.Integer, default=1)
    is_approved = db.Column(db.Boolean, default=False)
    approved_by = db.Column(db.String(200))
    approved_at = db.Column(db.DateTime)
    generation_error = db.Column(db.Text)
    generated_by_ai = db.Column(db.Boolean, default=False)
    submitted_at = db.Column(db.DateTime)
    bsi_reference = db.Column(db.String(100))
    updated_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def stage_label(self):
        labels = {
            'fruehwarnung': 'Frühwarnung (24h)',
            'zwischenmeldung': 'Zwischenmeldung (72h)',
            'abschlussbericht': 'Abschlussbericht (30 Tage)',
            'dsgvo_art33': 'DSGVO Art. 33 Meldung (72h)',
        }
        return labels.get(self.stage, self.stage)

    def __repr__(self):
        return f'<IncidentDraft {self.stage} v{self.version}>'


class IncidentTimeline(db.Model):
    """Audit-Log eines Incidents (unveränderlich)."""

    __tablename__ = 'nis2_incident_timeline'
    __table_args__ = {'schema': SCHEMA} if SCHEMA else {}

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer,
                            db.ForeignKey(f'{_sp}nis2_incidents.id', ondelete='CASCADE'),
                            nullable=False, index=True)

    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    performed_by = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<IncidentTimeline {self.action} at {self.timestamp}>'


# ─────────────────────────────────────────────────────────────────
# SUPPLY CHAIN
# ─────────────────────────────────────────────────────────────────

SUPPLIER_CATEGORIES = [
    ('it_service', 'IT-Dienstleister'),
    ('cloud', 'Cloud-Anbieter'),
    ('software', 'Software-Hersteller'),
    ('hardware', 'Hardware-Lieferant'),
    ('logistics', 'Logistik / Transport'),
    ('raw_materials', 'Rohstoff / Zulieferer'),
    ('consulting', 'Beratung / Dienstleistung'),
    ('other', 'Sonstiger Lieferant'),
]

CRITICALITY_LEVELS = [
    ('critical', 'Kritisch — essentiell für Betrieb'),
    ('high', 'Hoch — wichtiger Prozess'),
    ('medium', 'Mittel — unterstützender Prozess'),
    ('low', 'Niedrig — nicht kritisch'),
]


class Supplier(db.Model):
    """Lieferant / Dienstleister im Kontext §30 Nr. 4 BSIG."""

    __tablename__ = 'nis2_suppliers'
    __table_args__ = {'schema': SCHEMA} if SCHEMA else {}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}users.id', ondelete='CASCADE'),
                        nullable=False, index=True)

    # Identification
    company_name = db.Column(db.String(300), nullable=False)
    name = db.synonym('company_name')  # convenience alias used in routes/templates
    vat_id = db.Column(db.String(30))
    vat_number = db.synonym('vat_id')  # convenience alias
    country = db.Column(db.String(5))
    domain = db.Column(db.String(255))
    contact_email = db.Column(db.String(200))
    category = db.Column(db.String(30))
    criticality = db.Column(db.String(20), default='medium')
    services_provided = db.Column(db.Text)
    contract_start = db.Column(db.Date)

    # Verification results (from existing VAT/sanctions services)
    vies_valid = db.Column(db.Boolean)
    sanctions_clear = db.Column(db.Boolean)
    registry_active = db.Column(db.Boolean)
    last_verification_at = db.Column(db.DateTime)

    # Security assessment
    security_score = db.Column(db.Float)
    iso27001_certified = db.synonym('has_iso27001')  # alias
    has_iso27001 = db.Column(db.Boolean, default=False)
    has_soc2 = db.Column(db.Boolean, default=False)
    has_bsi_grundschutz = db.Column(db.Boolean, default=False)
    tls_grade = db.Column(db.String(5))
    last_security_scan_at = db.Column(db.DateTime)

    # AVV (Auftragsverarbeitungsvertrag) tracking — DSGVO Art. 28
    avv_exists = db.Column(db.Boolean, default=False)
    avv_signed = db.synonym('avv_exists')   # convenience alias
    avv_signed_at = db.Column(db.Date)
    avv_date = db.synonym('avv_signed_at')  # convenience alias
    avv_review_due = db.Column(db.Date)
    avv_expiry = db.synonym('avv_review_due')  # convenience alias

    # Composite risk score (0-100, higher = more risky)
    risk_score = db.Column(db.Float)
    risk_factors_json = db.Column(db.Text)

    # Additional tracking
    last_assessment_at = db.Column(db.DateTime)
    last_verified_at = db.synonym('last_verification_at')  # alias
    verification_results_json = db.Column(db.Text)  # raw JSON from VAT/sanctions check
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assessments = db.relationship('SupplierAssessment', backref='supplier', lazy='dynamic',
                                  cascade='all, delete-orphan',
                                  order_by='SupplierAssessment.assessed_at.desc()')

    def get_risk_factors(self):
        try:
            return json.loads(self.risk_factors_json) if self.risk_factors_json else []
        except (json.JSONDecodeError, TypeError):
            return []

    @property
    def avv_overdue(self):
        if not self.avv_exists or not self.avv_review_due:
            return False
        return date.today() > self.avv_review_due

    @property
    def risk_color(self):
        if self.risk_score is None:
            return 'secondary'
        if self.risk_score >= 70:
            return 'danger'
        if self.risk_score >= 40:
            return 'warning'
        return 'success'

    @property
    def verification_issues(self):
        issues = []
        if self.vies_valid is False:
            issues.append('VAT-Nummer ungültig')
        if self.sanctions_clear is False:
            issues.append('Sanktionstreffer')
        if self.registry_active is False:
            issues.append('Nicht im Handelsregister aktiv')
        return issues

    def __repr__(self):
        return f'<Supplier {self.company_name}>'


class SupplierAssessment(db.Model):
    """Snapshot einer Lieferantenbewertung."""

    __tablename__ = 'nis2_supplier_assessments'
    __table_args__ = {'schema': SCHEMA} if SCHEMA else {}

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer,
                            db.ForeignKey(f'{_sp}nis2_suppliers.id', ondelete='CASCADE'),
                            nullable=False, index=True)

    assessment_type = db.Column(db.String(30), default='initial')  # initial | quarterly | annual
    risk_score = db.Column(db.Float)
    score = db.synonym('risk_score')   # alias used in routes
    security_score = db.Column(db.Float)
    findings_json = db.Column(db.Text)
    notes = db.Column(db.Text)
    assessed_by = db.Column(db.Integer)
    triggered_by = db.Column(db.String(20), default='manual')  # manual | scheduler

    assessed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_findings(self):
        try:
            return json.loads(self.findings_json) if self.findings_json else []
        except (json.JSONDecodeError, TypeError):
            return []

    def __repr__(self):
        return f'<SupplierAssessment supplier={self.supplier_id} score={self.risk_score}>'


# ─────────────────────────────────────────────────────────────────
# SECURITY AWARENESS TRAINING (§30 Nr. 7 BSIG)
# ─────────────────────────────────────────────────────────────────

TRAINING_TOPICS = [
    ('phishing',         'Phishing & Social Engineering'),
    ('passwords',        'Sichere Passwörter & MFA'),
    ('ransomware',       'Ransomware & Malware'),
    ('data_protection',  'Datenschutz & DSGVO'),
    ('remote_work',      'Sicheres Homeoffice & VPN'),
    ('social_media',     'Social Media & OSINT-Risiken'),
    ('incident',         'Vorfallmeldung & Notfallprozesse'),
    ('access_control',   'Zugangskontrolle & Berechtigungen'),
    ('cloud_security',   'Cloud-Sicherheit'),
    ('general',          'Allgemeine Cybersicherheit'),
]


class SecurityTraining(db.Model):
    """
    Pflichtunterweisung / Security-Awareness-Schulung (§30 Abs. 2 Nr. 7 BSIG).
    Wird per Email an Teammitglieder versendet; Lesebestätigung mit Token.
    """

    __tablename__ = 'nis2_trainings'
    __table_args__ = {'schema': SCHEMA} if SCHEMA else {}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{_sp}users.id', ondelete='CASCADE'),
                        nullable=False, index=True)

    title = db.Column(db.String(300), nullable=False)
    topic = db.Column(db.String(50), default='general')

    # Content — Markdown lecture text
    content_md = db.Column(db.Text, nullable=False)

    # Summary shown on acknowledgment page (auto-extract or manual)
    summary = db.Column(db.Text)

    # Audience (free text or JSON list of emails)
    audience_json = db.Column(db.Text)          # JSON list of {name, email}

    # Status: draft | sent | closed
    status = db.Column(db.String(20), default='draft', index=True)

    # Deadline for acknowledgment
    due_date = db.Column(db.Date)

    # Sent / closed timestamps
    sent_at = db.Column(db.DateTime)
    closed_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    acknowledgments = db.relationship(
        'TrainingAcknowledgment', backref='training',
        lazy='dynamic', cascade='all, delete-orphan',
    )

    def get_audience(self):
        try:
            return json.loads(self.audience_json) if self.audience_json else []
        except (json.JSONDecodeError, TypeError):
            return []

    def set_audience(self, audience_list):
        self.audience_json = json.dumps(audience_list, ensure_ascii=False)

    @property
    def ack_count(self):
        return self.acknowledgments.filter_by(acknowledged=True).count()

    @property
    def sent_count(self):
        return self.acknowledgments.count()

    @property
    def topic_label(self):
        return dict(TRAINING_TOPICS).get(self.topic, self.topic)

    def __repr__(self):
        return f'<SecurityTraining {self.id} "{self.title}" [{self.status}]>'


class TrainingAcknowledgment(db.Model):
    """
    Lesebestätigung eines Empfängers (§30 Nr. 7 BSIG Nachweis).
    Token-basiert — kein Login erforderlich.
    """

    __tablename__ = 'nis2_training_acks'
    __table_args__ = {'schema': SCHEMA} if SCHEMA else {}

    id = db.Column(db.Integer, primary_key=True)
    training_id = db.Column(db.Integer,
                            db.ForeignKey(f'{_sp}nis2_trainings.id', ondelete='CASCADE'),
                            nullable=False, index=True)

    # Recipient info
    recipient_name = db.Column(db.String(200), nullable=False)
    recipient_email = db.Column(db.String(200), nullable=False)

    # Unique token for the acknowledgment link (UUID)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)

    # Tracking
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    opened_at = db.Column(db.DateTime)     # first click on link
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_at = db.Column(db.DateTime)
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6

    # Optional: typed confirmation name ("Ich, Max Mustermann, bestätige...")
    confirmed_name = db.Column(db.String(200))

    def __repr__(self):
        return (f'<TrainingAck training={self.training_id} '
                f'email={self.recipient_email} ack={self.acknowledged}>')


# ─────────────────────────────────────────────────────────────────
# NIS2 SITE AUDIT  (§30 Nr. 3, 5 BSIG — Web-Security-Check)
# ─────────────────────────────────────────────────────────────────

class NIS2AuditJob(db.Model):
    """One full NIS2/DSGVO audit run per user per target domain."""

    __tablename__ = 'nis2_audit_jobs'
    __table_args__ = {'schema': SCHEMA} if SCHEMA else {}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey(f'{_sp}users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    target = db.Column(db.String(500), nullable=False)

    # pending | running | done | failed
    status = db.Column(db.String(20), default='pending', nullable=False)

    # Stored HTML report (generated when status → done)
    report_html = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    completed_at = db.Column(db.DateTime)

    # relationships
    findings = db.relationship(
        'NIS2Finding', backref='job', lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='NIS2Finding.severity_rank',
    )
    logs = db.relationship(
        'NIS2AuditLog', backref='job', lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='NIS2AuditLog.id',
    )
    tasks = db.relationship(
        'NIS2AuditTask', backref='job', lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='NIS2AuditTask.id',
    )

    def __repr__(self):
        return f'<NIS2AuditJob id={self.id} target={self.target} status={self.status}>'


class NIS2Finding(db.Model):
    """Security / compliance finding from an audit run."""

    __tablename__ = 'nis2_audit_findings'
    __table_args__ = {'schema': SCHEMA} if SCHEMA else {}

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(
        db.Integer,
        db.ForeignKey(f'{_sp}nis2_audit_jobs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    severity = db.Column(db.String(20), default='info')   # critical/high/medium/low/info
    severity_rank = db.Column(db.Integer, default=5)       # 1=critical … 5=info
    cvss = db.Column(db.String(30))
    dsgvo_article = db.Column(db.String(200))
    recommendation = db.Column(db.Text)
    target_url = db.Column(db.String(500))
    tool = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<NIS2Finding [{self.severity.upper()}] {self.title[:60]}>'


class NIS2AuditLog(db.Model):
    """Real-time log line for a running audit (polled by frontend)."""

    __tablename__ = 'nis2_audit_logs'
    __table_args__ = {'schema': SCHEMA} if SCHEMA else {}

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(
        db.Integer,
        db.ForeignKey(f'{_sp}nis2_audit_jobs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    level = db.Column(db.String(20), default='INFO')   # INFO|CMD|FINDING|AGENT|ERROR|TOOLS_USED
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<NIS2AuditLog [{self.level}] {(self.message or "")[:60]}>'


class NIS2AuditTask(db.Model):
    """NIS2/DSGVO compliance checklist task linked to one audit job."""

    __tablename__ = 'nis2_audit_tasks'
    __table_args__ = {'schema': SCHEMA} if SCHEMA else {}

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(
        db.Integer,
        db.ForeignKey(f'{_sp}nis2_audit_jobs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    category = db.Column(db.String(50))        # Technisch | Organisatorisch | DSGVO
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    nis2_ref = db.Column(db.String(100))
    dsgvo_ref = db.Column(db.String(100))
    required = db.Column(db.Boolean, default=True)
    done = db.Column(db.Boolean, default=False)
    done_at = db.Column(db.DateTime)
    notes = db.Column(db.String(500))

    def __repr__(self):
        return f'<NIS2AuditTask [{self.category}] {self.title[:50]} done={self.done}>'
