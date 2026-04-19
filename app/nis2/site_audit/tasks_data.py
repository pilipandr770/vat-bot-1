"""
NIS2 / DSGVO Standard Compliance Tasks
=======================================
26 tasks in 3 categories mirroring §30 BSIG / DSGVO requirements.
Originally from NIS2-SDWGO — adapted for vat-verifizierung.de platform.
"""

from __future__ import annotations
from typing import List, Dict, Any

NIS2_STANDARD_TASKS: List[Dict[str, Any]] = [
    # ── Technisch (§30 Abs. 2 Nr. 3, 5, 6 BSIG) ─────────────────────────
    {
        "category": "Technisch",
        "title": "HTTP Security Headers",
        "description": (
            "Prüfung auf: Content-Security-Policy, Strict-Transport-Security, "
            "X-Frame-Options, X-Content-Type-Options, Referrer-Policy, "
            "Permissions-Policy, X-XSS-Protection."
        ),
        "nis2_ref": "§30 Nr. 3 BSIG",
        "dsgvo_ref": "Art. 32 DSGVO",
        "required": True,
    },
    {
        "category": "Technisch",
        "title": "TLS/SSL-Konfiguration",
        "description": (
            "TLS 1.2+, gültiges Zertifikat, HSTS, kein veraltetes Cipher-Suite."
        ),
        "nis2_ref": "§30 Nr. 3 BSIG",
        "dsgvo_ref": "Art. 32 Abs. 1 lit. a DSGVO",
        "required": True,
    },
    {
        "category": "Technisch",
        "title": "Web-Security-Check (OWASP Top 10)",
        "description": (
            "Prüfung auf SQL-Injection, XSS, CSRF, unsichere Direktumleitungen, "
            "exponierte sensible Daten."
        ),
        "nis2_ref": "§30 Nr. 3, 5 BSIG",
        "dsgvo_ref": "Art. 32 DSGVO",
        "required": True,
    },
    {
        "category": "Technisch",
        "title": "Schwachstellen-Scan (CVE-Datenbank)",
        "description": (
            "Automatisierter Scan auf bekannte CVEs in verwendeten Komponenten."
        ),
        "nis2_ref": "§30 Nr. 5 BSIG",
        "dsgvo_ref": "",
        "required": True,
    },
    {
        "category": "Technisch",
        "title": "Port-Scan & Service-Analyse",
        "description": (
            "Erkennung offener Ports und exponierter Dienste (SSH, RDP, DB-Ports etc.)."
        ),
        "nis2_ref": "§30 Nr. 3, 6 BSIG",
        "dsgvo_ref": "",
        "required": True,
    },
    {
        "category": "Technisch",
        "title": "MFA / IAM-Prüfung",
        "description": (
            "Multi-Faktor-Authentifizierung für Admin-Zugänge; "
            "Rollenprinzip (Least Privilege)."
        ),
        "nis2_ref": "§30 Nr. 1 BSIG",
        "dsgvo_ref": "Art. 32 Abs. 1 lit. b DSGVO",
        "required": True,
    },
    {
        "category": "Technisch",
        "title": "Datenverschlüsselung (at rest & in transit)",
        "description": (
            "Verschlüsselung sensibler Daten in Datenbanken (AES-256) und "
            "bei der Übertragung (TLS 1.2+)."
        ),
        "nis2_ref": "§30 Nr. 3 BSIG",
        "dsgvo_ref": "Art. 32 Abs. 1 lit. a DSGVO",
        "required": True,
    },
    {
        "category": "Technisch",
        "title": "Backup & Wiederherstellungskonzept",
        "description": (
            "Regelmäßige Datensicherungen, Backup-Verschlüsselung, "
            "getestete Wiederherstellungsprozesse (RTO/RPO)."
        ),
        "nis2_ref": "§30 Nr. 2 BSIG",
        "dsgvo_ref": "Art. 32 Abs. 1 lit. c DSGVO",
        "required": True,
    },
    {
        "category": "Technisch",
        "title": "Logging & SIEM-Integration",
        "description": (
            "Zentrale Protokollierung (SIEM), Anomalie-Erkennung, "
            "Log-Aufbewahrung ≥ 12 Monate."
        ),
        "nis2_ref": "§30 Nr. 6 BSIG",
        "dsgvo_ref": "Art. 5 Abs. 2 DSGVO (Rechenschaftspflicht)",
        "required": True,
    },
    {
        "category": "Technisch",
        "title": "Patch-Management",
        "description": (
            "Systematisches Update-Management, CVE-Monitoring, "
            "SLA für kritische Patches (≤ 72h)."
        ),
        "nis2_ref": "§30 Nr. 5 BSIG",
        "dsgvo_ref": "",
        "required": True,
    },
    {
        "category": "Technisch",
        "title": "Subdomain- & DNS-Sicherheit",
        "description": (
            "SPF, DMARC, DKIM, DNSSEC; Schutz vor Subdomain-Takeover."
        ),
        "nis2_ref": "§30 Nr. 3, 6 BSIG",
        "dsgvo_ref": "",
        "required": True,
    },

    # ── Organisatorisch (§30 Abs. 2 Nr. 1–4, 7–10 BSIG) ────────────────
    {
        "category": "Organisatorisch",
        "title": "Risikoanalyse & -bewertung",
        "description": (
            "Dokumentierte Risikoanalyse (ISO 27001 oder BSI IT-Grundschutz), "
            "jährliche Überprüfung."
        ),
        "nis2_ref": "§30 Nr. 1 BSIG",
        "dsgvo_ref": "Art. 35 DSGVO (DSFA bei Hochrisiko)",
        "required": True,
    },
    {
        "category": "Organisatorisch",
        "title": "ISMS-Richtlinien & -Verfahren",
        "description": (
            "Dokumentiertes Informationssicherheitsmanagementsystem (ISMS), "
            "Security-Policy, Acceptable-Use-Policy."
        ),
        "nis2_ref": "§30 Nr. 1 BSIG",
        "dsgvo_ref": "",
        "required": True,
    },
    {
        "category": "Organisatorisch",
        "title": "Incident-Response-Plan (IRP)",
        "description": (
            "Dokumentierter IRP mit Eskalationswegen, "
            "BSI-Meldepflicht (24h/72h), Playbooks für typische Vorfälle."
        ),
        "nis2_ref": "§30 Nr. 2, §32 BSIG",
        "dsgvo_ref": "Art. 33 DSGVO (72h-Meldung)",
        "required": True,
    },
    {
        "category": "Organisatorisch",
        "title": "Business-Continuity & Notfallplan (BCP/DRP)",
        "description": (
            "Notfallplan, DR-Konzept, dokumentierte RTO/RPO-Ziele, "
            "jährliche Übungen."
        ),
        "nis2_ref": "§30 Nr. 2 BSIG",
        "dsgvo_ref": "Art. 32 Abs. 1 lit. c DSGVO",
        "required": True,
    },
    {
        "category": "Organisatorisch",
        "title": "Supply-Chain-Sicherheit",
        "description": (
            "Sicherheitsanforderungen für Lieferanten, SLAs für Drittanbieter, "
            "regelmäßige Bewertung kritischer Zulieferer."
        ),
        "nis2_ref": "§30 Nr. 4 BSIG",
        "dsgvo_ref": "Art. 28 DSGVO (AV-Vertrag)",
        "required": True,
    },
    {
        "category": "Organisatorisch",
        "title": "Mitarbeiterschulung & Security-Awareness",
        "description": (
            "Regelmäßige Schulungen (§38 BSIG: GF-Haftung), "
            "Phishing-Simulationen, Nachweis-Dokumentation."
        ),
        "nis2_ref": "§30 Nr. 7, §38 BSIG",
        "dsgvo_ref": "Art. 39 DSGVO",
        "required": True,
    },
    {
        "category": "Organisatorisch",
        "title": "Asset-Management",
        "description": (
            "Vollständiges Inventar aller IT-Assets (Hardware, Software, Cloud), "
            "Klassifizierung nach Kritikalität."
        ),
        "nis2_ref": "§30 Nr. 3 BSIG",
        "dsgvo_ref": "",
        "required": True,
    },
    {
        "category": "Organisatorisch",
        "title": "Physische Sicherheit",
        "description": (
            "Zugangskontrolle zu Serverräumen/RZ, Überwachung, "
            "Schutz vor physischem Zugriff."
        ),
        "nis2_ref": "§30 Nr. 8 BSIG",
        "dsgvo_ref": "Art. 32 Abs. 1 lit. b DSGVO",
        "required": True,
    },

    # ── DSGVO ──────────────────────────────────────────────────────────
    {
        "category": "DSGVO",
        "title": "Datenschutzerklärung",
        "description": (
            "Rechtskonforme Datenschutzerklärung (Art. 13/14 DSGVO), "
            "deutsch & aktuell, vollständige Zweckangaben."
        ),
        "nis2_ref": "",
        "dsgvo_ref": "Art. 13, 14 DSGVO",
        "required": True,
    },
    {
        "category": "DSGVO",
        "title": "Verzeichnis von Verarbeitungstätigkeiten (VVT)",
        "description": (
            "Dokumentiertes VVT nach Art. 30 DSGVO, "
            "gepflegt für alle Verarbeitungen mit Zweck, Rechtsgrundlage, Fristen."
        ),
        "nis2_ref": "",
        "dsgvo_ref": "Art. 30 DSGVO",
        "required": True,
    },
    {
        "category": "DSGVO",
        "title": "Auftragsverarbeitungsverträge (AVV)",
        "description": (
            "Geschlossene AVVs mit allen Auftragsverarbeitern (Cloud, Analytics, "
            "E-Mail-Anbieter etc.), geprüfte Standardvertragsklauseln (SCC)."
        ),
        "nis2_ref": "§30 Nr. 4 BSIG",
        "dsgvo_ref": "Art. 28 DSGVO",
        "required": True,
    },
    {
        "category": "DSGVO",
        "title": "Cookie-Consent & DSGVO-konformes Tracking",
        "description": (
            "DSGVO-konformes Cookie-Banner (Opt-In), kein Pre-Ticking, "
            "Widerrufsmöglichkeit, kein Tracking ohne Einwilligung."
        ),
        "nis2_ref": "",
        "dsgvo_ref": "Art. 6, 7 DSGVO; §25 TTDSG",
        "required": True,
    },
    {
        "category": "DSGVO",
        "title": "Datenschutz-Folgenabschätzung (DSFA)",
        "description": (
            "DSFA für Hochrisiko-Verarbeitungen (Art. 35 DSGVO), "
            "dokumentiert und genehmigt."
        ),
        "nis2_ref": "",
        "dsgvo_ref": "Art. 35 DSGVO",
        "required": False,
    },
    {
        "category": "DSGVO",
        "title": "Datenschutzbeauftragter (DSB)",
        "description": (
            "Bestellung eines DSB (intern oder extern) bei Pflicht, "
            "Meldung an Aufsichtsbehörde."
        ),
        "nis2_ref": "",
        "dsgvo_ref": "Art. 37–39 DSGVO",
        "required": False,
    },
    {
        "category": "DSGVO",
        "title": "Betroffenenrechte-Management",
        "description": (
            "Prozess für Auskunft, Löschung, Berichtigung, Widerspruch (Art. 15–22 DSGVO); "
            "Frist 30 Tage."
        ),
        "nis2_ref": "",
        "dsgvo_ref": "Art. 15–22 DSGVO",
        "required": True,
    },
]
