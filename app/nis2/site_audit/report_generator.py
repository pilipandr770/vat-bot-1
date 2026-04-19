"""
NIS2 Site Audit — HTML Report Generator
=========================================
Generates a professional 9-section NIS2/DSGVO compliance report as HTML.
The report is printable to PDF via browser (Ctrl+P / Print to PDF).

Platform branding: vat-verifizierung.de
Auftraggeber (client): current_user data

Adapted from NIS2-SDWGO pdf_generator.py
(https://github.com/pilipandr770/NIS2-SDWGO).
Hardcoded "AndriiIT" constants replaced with platform/user parameters.
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Platform constants (Prüfer / Auftragnehmer)
# ---------------------------------------------------------------------------
PLATFORM_NAME     = "vat-verifizierung.de"
PLATFORM_FULL     = "vat-verifizierung.de | NIS2 Compliance Platform"
PLATFORM_WEBSITE  = "https://www.vat-verifizierung.de"
PLATFORM_EMAIL    = "support@vat-verifizierung.de"

# ---------------------------------------------------------------------------
# Severity styles
# ---------------------------------------------------------------------------
_SEVERITY_STYLE = {
    "critical": ("🔴 KRITISCH", "#c0392b", "#fdecea"),
    "high":     ("🟠 HOCH",     "#e67e22", "#fef5e7"),
    "medium":   ("🟡 MITTEL",   "#f39c12", "#fefde7"),
    "low":      ("🔵 NIEDRIG",  "#2980b9", "#eaf4fb"),
    "info":     ("ℹ️ INFO",      "#7f8c8d", "#f4f6f7"),
}


def _sev(severity: str):
    return _SEVERITY_STYLE.get(severity.lower(), _SEVERITY_STYLE["info"])


def _e(text: Optional[str]) -> str:
    """HTML-escape helper."""
    return html.escape(str(text or ""), quote=True)


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _section_cover(target: str, client_info: Dict, checked_at: str) -> str:
    company = _e(client_info.get("company", "—"))
    address = _e(client_info.get("address", ""))
    email   = _e(client_info.get("email", ""))
    phone   = _e(client_info.get("phone", ""))
    ust_id  = _e(client_info.get("ust_id", ""))

    return f"""
<div class="cover-page">
  <div class="cover-header">
    <div class="platform-brand">{_e(PLATFORM_FULL)}</div>
    <h1 class="report-title">NIS2 / DSGVO<br>Sicherheits-Audit-Bericht</h1>
    <p class="report-subtitle">Web-Security-Check &amp; Compliance-Analyse</p>
  </div>
  <div class="cover-meta">
    <table class="meta-table">
      <tr><th>Prüfziel (URL)</th><td><code>{_e(target)}</code></td></tr>
      <tr><th>Auftraggeber</th><td>{company}</td></tr>
      {"<tr><th>Adresse</th><td>" + address + "</td></tr>" if address else ""}
      {"<tr><th>E-Mail</th><td>" + email + "</td></tr>" if email else ""}
      {"<tr><th>Telefon</th><td>" + phone + "</td></tr>" if phone else ""}
      {"<tr><th>USt-IdNr.</th><td>" + ust_id + "</td></tr>" if ust_id else ""}
      <tr><th>Prüfdatum</th><td>{_e(checked_at)}</td></tr>
      <tr><th>Auftragnehmer</th><td>{_e(PLATFORM_FULL)}</td></tr>
      <tr><th>Plattform</th><td><a href="{_e(PLATFORM_WEBSITE)}">{_e(PLATFORM_WEBSITE)}</a></td></tr>
      <tr><th>Kontakt</th><td>{_e(PLATFORM_EMAIL)}</td></tr>
    </table>
  </div>
  <div class="cover-footer">
    <p>Vertraulich — nur für den Auftraggeber bestimmt</p>
    <p>Erstellt von {_e(PLATFORM_NAME)} &bull; {_e(checked_at)}</p>
  </div>
</div>
"""


def _section_summary(findings: List[Dict], tasks: List[Dict], live: Dict) -> str:
    total = len(findings)
    critical = sum(1 for f in findings if f.get("severity") == "critical")
    high     = sum(1 for f in findings if f.get("severity") == "high")
    medium   = sum(1 for f in findings if f.get("severity") == "medium")
    low      = sum(1 for f in findings if f.get("severity") == "low")
    info_cnt = sum(1 for f in findings if f.get("severity") == "info")

    done_tasks = sum(1 for t in tasks if t.get("done"))
    total_tasks = len(tasks)
    compliance_pct = int(done_tasks / total_tasks * 100) if total_tasks else 0

    warnings = live.get("warning_count", 0)
    tls_ok = live.get("tls", {}).get("valid", None)
    tls_badge = (
        '<span class="badge badge-ok">✅ Gültig</span>' if tls_ok
        else '<span class="badge badge-fail">❌ Ungültig / Fehler</span>'
        if tls_ok is False
        else '<span class="badge badge-warn">⚠️ Nicht geprüft</span>'
    )

    return f"""
<section class="report-section">
  <h2>1. Management Summary</h2>
  <div class="summary-grid">
    <div class="summary-card card-critical">
      <div class="card-number">{critical}</div>
      <div class="card-label">Kritische Findings</div>
    </div>
    <div class="summary-card card-high">
      <div class="card-number">{high}</div>
      <div class="card-label">Hohe Findings</div>
    </div>
    <div class="summary-card card-medium">
      <div class="card-number">{medium}</div>
      <div class="card-label">Mittlere Findings</div>
    </div>
    <div class="summary-card card-low">
      <div class="card-number">{low + info_cnt}</div>
      <div class="card-label">Niedrige / Info</div>
    </div>
  </div>

  <table class="info-table">
    <tr><th>Gesamtanzahl Findings</th><td>{total}</td></tr>
    <tr><th>Warnungen (Live-Check)</th><td>{warnings}</td></tr>
    <tr><th>TLS/SSL-Zertifikat</th><td>{tls_badge}</td></tr>
    <tr><th>NIS2-Compliance-Score</th>
      <td>
        <div class="progress-bar">
          <div class="progress-fill" style="width:{compliance_pct}%">{compliance_pct}%</div>
        </div>
        {done_tasks} / {total_tasks} Tasks erfüllt
      </td>
    </tr>
  </table>

  {"<div class='alert alert-critical'>⚠️ <strong>Kritische Schwachstellen gefunden!</strong> Sofortiger Handlungsbedarf gemäß §30 BSIG und Art. 32 DSGVO.</div>" if critical > 0 else ""}
  {"<div class='alert alert-high'>⚠️ <strong>Hohe Risiken gefunden.</strong> Behebung innerhalb von 30 Tagen empfohlen.</div>" if high > 0 and critical == 0 else ""}
  {"<div class='alert alert-ok'>✅ Keine kritischen oder hohen Schwachstellen gefunden. Weiter mit mittleren und niedrigen Findings.</div>" if critical == 0 and high == 0 else ""}
</section>
"""


def _section_scope(target: str, live: Dict) -> str:
    hostname = live.get("hostname", target)
    checked_at = live.get("checked_at", "—")
    tools_note = (
        "Eingesetzte Prüfmethoden: HTTP-Header-Analyse, TLS/SSL-Zertifikatsprüfung, "
        "Cookie-Security-Analyse, DNS-Security-Check (SPF/DMARC/DKIM/DNSSEC), "
        "KI-gestützte Analyse (Claude AI)."
    )

    return f"""
<section class="report-section">
  <h2>2. Prüfumfang &amp; Methodik</h2>
  <table class="info-table">
    <tr><th>Prüfziel</th><td><code>{_e(target)}</code></td></tr>
    <tr><th>Hostname</th><td>{_e(hostname)}</td></tr>
    <tr><th>Prüfdatum / -uhrzeit</th><td>{_e(checked_at)}</td></tr>
    <tr><th>Methodik</th><td>{_e(tools_note)}</td></tr>
    <tr><th>Normen</th><td>NIS2 (§30 BSIG), DSGVO Art. 32, OWASP Top 10, ISO/IEC 27001</td></tr>
  </table>
  <h3>Prüfbereiche</h3>
  <ul>
    <li>HTTP Security Headers (CSP, HSTS, X-Frame-Options, …)</li>
    <li>TLS/SSL-Konfiguration und Zertifikatsgültigkeit</li>
    <li>Cookie-Sicherheitsflags (HttpOnly, Secure, SameSite)</li>
    <li>DNS-Sicherheit: SPF, DMARC, DKIM, DNSSEC</li>
    <li>NIS2/DSGVO-Compliance-Checkliste (26 Prüfpunkte)</li>
    <li>KI-gestützte Analyse und Bewertung</li>
  </ul>
</section>
"""


def _section_live_check(live: Dict) -> str:
    http = live.get("http", {})
    tls  = live.get("tls", {})
    dns  = live.get("dns", {})

    # Headers table
    missing = http.get("missing_headers", [])
    present = http.get("present_headers", [])

    def header_rows():
        all_hdrs = sorted(set(missing + present))
        rows = []
        for h in all_hdrs:
            status = (
                '<span class="badge badge-ok">✅ Vorhanden</span>'
                if h in present
                else '<span class="badge badge-fail">❌ Fehlt</span>'
            )
            rows.append(f"<tr><td><code>{_e(h)}</code></td><td>{status}</td></tr>")
        return "\n".join(rows)

    tls_valid = tls.get("valid")
    tls_status = (
        '<span class="badge badge-ok">✅ Gültig</span>' if tls_valid
        else '<span class="badge badge-fail">❌ Ungültig</span>'
        if tls_valid is False
        else '<span class="badge badge-warn">⚠️ Nicht geprüft</span>'
    )

    spf_status = (
        '<span class="badge badge-ok">✅ SPF vorhanden</span>'
        if dns.get("spf") == "present"
        else '<span class="badge badge-fail">❌ Kein SPF</span>'
    )
    dmarc_status = (
        '<span class="badge badge-ok">✅ DMARC vorhanden</span>'
        if dns.get("dmarc") == "present"
        else '<span class="badge badge-fail">❌ Kein DMARC</span>'
    )
    dnssec_status = (
        '<span class="badge badge-ok">✅ DNSSEC aktiv</span>'
        if dns.get("dnssec")
        else '<span class="badge badge-fail">❌ Kein DNSSEC</span>'
    )

    warnings_html = ""
    all_warnings = live.get("warnings", [])
    if all_warnings:
        items = "\n".join(f"<li>{_e(w)}</li>" for w in all_warnings)
        warnings_html = f"<h3>⚠️ Warnungen ({len(all_warnings)})</h3><ul class='warning-list'>{items}</ul>"

    return f"""
<section class="report-section">
  <h2>3. Live-Check Ergebnisse</h2>

  <h3>HTTP Security Headers</h3>
  <table class="data-table">
    <thead><tr><th>Header</th><th>Status</th></tr></thead>
    <tbody>{header_rows()}</tbody>
  </table>
  <p>CSP-Stärke: <strong>{_e(http.get("csp_strength", "none"))}</strong>
  &nbsp;|&nbsp; HSTS: <strong>{"✅ Aktiv" if http.get("hsts_present") else "❌ Fehlt"}</strong>
  {"&nbsp;| max-age: " + str(http.get("hsts_max_age")) + "s" if http.get("hsts_max_age") else ""}</p>

  <h3>TLS/SSL-Zertifikat</h3>
  <table class="info-table">
    <tr><th>Status</th><td>{tls_status}</td></tr>
    <tr><th>Aussteller</th><td>{_e(tls.get("issuer", "—"))}</td></tr>
    <tr><th>Subject</th><td>{_e(tls.get("subject", "—"))}</td></tr>
    <tr><th>Ablaufdatum</th><td>{_e(tls.get("expiry", "—"))}</td></tr>
    <tr><th>Verbleibende Tage</th><td>{tls.get("days_remaining", "—")}</td></tr>
  </table>

  <h3>DNS-Sicherheit</h3>
  <table class="info-table">
    <tr><th>SPF</th><td>{spf_status}</td></tr>
    {"<tr><th>SPF-Record</th><td><code>" + _e(dns.get("spf_raw","")) + "</code></td></tr>" if dns.get("spf_raw") else ""}
    <tr><th>DMARC</th><td>{dmarc_status}</td></tr>
    {"<tr><th>DMARC-Record</th><td><code>" + _e(dns.get("dmarc_raw","")) + "</code></td></tr>" if dns.get("dmarc_raw") else ""}
    <tr><th>DNSSEC</th><td>{dnssec_status}</td></tr>
  </table>

  {warnings_html}
</section>
"""


def _section_findings(findings: List[Dict]) -> str:
    if not findings:
        return """
<section class="report-section">
  <h2>4. Technische Findings</h2>
  <p class="no-findings">✅ Keine Findings gefunden.</p>
</section>
"""

    rows = []
    for i, f in enumerate(findings, 1):
        label, color, bg = _sev(f.get("severity", "info"))
        cvss = f.get("cvss", "")
        dsgvo = f.get("dsgvo_article", "")
        rows.append(f"""
<div class="finding" style="border-left:4px solid {color}; background:{bg}">
  <div class="finding-header">
    <span class="finding-num">#{i}</span>
    <span class="finding-sev" style="color:{color}">{label}</span>
    {"<span class='cvss'>CVSS: " + _e(cvss) + "</span>" if cvss else ""}
    {"<span class='dsgvo-ref'>" + _e(dsgvo) + "</span>" if dsgvo else ""}
    <span class="finding-tool">Tool: {_e(f.get("tool","ai"))}</span>
  </div>
  <h4 class="finding-title">{_e(f.get("title",""))}</h4>
  <p class="finding-desc">{_e(f.get("description",""))}</p>
  <div class="finding-rec">
    <strong>🛠 Empfehlung:</strong> {_e(f.get("recommendation",""))}
  </div>
</div>""")

    return f"""
<section class="report-section">
  <h2>4. Technische Findings ({len(findings)})</h2>
  {"".join(rows)}
</section>
"""


def _section_checklist(tasks: List[Dict]) -> str:
    categories = ["Technisch", "Organisatorisch", "DSGVO"]
    parts = []
    for cat in categories:
        cat_tasks = [t for t in tasks if t.get("category") == cat]
        if not cat_tasks:
            continue
        done = sum(1 for t in cat_tasks if t.get("done"))
        pct = int(done / len(cat_tasks) * 100) if cat_tasks else 0

        rows = []
        for t in cat_tasks:
            icon = "✅" if t.get("done") else "⬜"
            rows.append(f"""
<tr class="{'task-done' if t.get('done') else 'task-todo'}">
  <td>{icon}</td>
  <td><strong>{_e(t["title"])}</strong><br><small>{_e(t.get("description",""))}</small></td>
  <td><small>{_e(t.get("nis2_ref",""))}</small></td>
  <td><small>{_e(t.get("dsgvo_ref",""))}</small></td>
  <td><small>{_e(t.get("notes",""))}</small></td>
</tr>""")

        parts.append(f"""
<h3>{cat} — {done}/{len(cat_tasks)} ({pct}%)</h3>
<div class="progress-bar"><div class="progress-fill" style="width:{pct}%">{pct}%</div></div>
<table class="checklist-table">
  <thead><tr><th>Status</th><th>Aufgabe</th><th>NIS2-Ref</th><th>DSGVO-Ref</th><th>Notizen</th></tr></thead>
  <tbody>{"".join(rows)}</tbody>
</table>""")

    total_done = sum(1 for t in tasks if t.get("done"))
    total_pct = int(total_done / len(tasks) * 100) if tasks else 0

    return f"""
<section class="report-section">
  <h2>5. NIS2/DSGVO-Compliance-Checkliste</h2>
  <p><strong>Gesamt-Compliance: {total_done}/{len(tasks)} ({total_pct}%)</strong></p>
  <div class="progress-bar progress-large">
    <div class="progress-fill" style="width:{total_pct}%">{total_pct}%</div>
  </div>
  {"".join(parts)}
</section>
"""


def _section_dsgvo(live: Dict, findings: List[Dict]) -> str:
    dsgvo_findings = [
        f for f in findings if f.get("dsgvo_article")
    ]
    items = ""
    if dsgvo_findings:
        rows = "\n".join(
            f"<tr><td>{_e(f['title'])}</td><td>{_e(f.get('dsgvo_article',''))}</td>"
            f"<td>{_e(f.get('recommendation',''))}</td></tr>"
            for f in dsgvo_findings
        )
        items = f"""
<table class="data-table">
  <thead><tr><th>Finding</th><th>DSGVO-Artikel</th><th>Empfehlung</th></tr></thead>
  <tbody>{rows}</tbody>
</table>"""
    else:
        items = "<p>Keine DSGVO-relevanten Findings aus dem technischen Scan.</p>"

    return f"""
<section class="report-section">
  <h2>6. DSGVO-Analyse (Art. 32)</h2>
  <p>
    Gemäß Art. 32 DSGVO sind geeignete technische und organisatorische Maßnahmen (TOMs)
    zu implementieren, um ein dem Risiko angemessenes Schutzniveau zu gewährleisten.
  </p>
  <h3>Relevante Findings mit DSGVO-Bezug</h3>
  {items}
  <h3>TOM-Bewertung</h3>
  <table class="info-table">
    <tr><th>Verschlüsselung (Art. 32 Abs. 1 lit. a)</th>
        <td>{"✅ TLS aktiv" if live.get("tls",{}).get("valid") else "⚠️ TLS-Problem"}</td></tr>
    <tr><th>Vertraulichkeit &amp; Integrität (Art. 32 Abs. 1 lit. b)</th>
        <td>{"✅ Security Headers vorhanden" if live.get("http",{}).get("present_headers") else "⚠️ Security Headers fehlen"}</td></tr>
    <tr><th>Belastbarkeit (Art. 32 Abs. 1 lit. c)</th>
        <td>Manuelle Prüfung erforderlich (Backup, DR-Plan)</td></tr>
    <tr><th>Wiederherstellbarkeit (Art. 32 Abs. 1 lit. c)</th>
        <td>Manuelle Prüfung erforderlich (RTO/RPO-Dokumentation)</td></tr>
  </table>
</section>
"""


def _section_recommendations(findings: List[Dict]) -> str:
    critical = [f for f in findings if f.get("severity") == "critical"]
    high     = [f for f in findings if f.get("severity") == "high"]
    medium   = [f for f in findings if f.get("severity") == "medium"]

    def _rec_list(items, label, color):
        if not items:
            return ""
        rows = "\n".join(
            f"<li><strong>{_e(f['title'])}</strong>: {_e(f.get('recommendation',''))}</li>"
            for f in items
        )
        return f"<h3 style='color:{color}'>{label}</h3><ol>{rows}</ol>"

    no_recs = not critical and not high and not medium

    return f"""
<section class="report-section">
  <h2>7. Empfehlungen &amp; Maßnahmenplan</h2>
  {"<p class='no-findings'>✅ Keine dringenden Maßnahmen erforderlich.</p>" if no_recs else ""}
  {_rec_list(critical, "🔴 Sofortmaßnahmen (kritisch)", "#c0392b")}
  {_rec_list(high,     "🟠 Kurzfristig (30 Tage)", "#e67e22")}
  {_rec_list(medium,   "🟡 Mittelfristig (90 Tage)", "#f39c12")}

  <h3>Allgemeine NIS2-Empfehlungen</h3>
  <ul>
    <li>Implementieren Sie ein ISMS nach ISO/IEC 27001 oder BSI IT-Grundschutz</li>
    <li>Führen Sie regelmäßige Penetrationstests durch (min. 1x jährlich)</li>
    <li>Schulen Sie Mitarbeiter zu Informationssicherheit (§38 BSIG: GF-Haftung)</li>
    <li>Prüfen Sie alle Auftragsverarbeiter auf DSGVO-Konformität (Art. 28 DSGVO)</li>
    <li>Registrieren Sie sich beim BSI MUK-Portal (§33 BSIG) bei NIS2-Pflicht</li>
  </ul>
</section>
"""


def _section_protocol(logs: List[Dict], tools_used: List[str]) -> str:
    log_rows = ""
    for lg in logs[:100]:  # Cap at 100 lines
        level = lg.get("level", "INFO")
        msg   = lg.get("message", "")
        ts    = lg.get("created_at", "")
        badge_class = {
            "ERROR": "badge-fail",
            "FINDING": "badge-warn",
            "AGENT": "badge-agent",
            "CMD": "badge-cmd",
        }.get(level, "badge-info")
        log_rows += f"""<tr>
  <td class="log-ts"><small>{_e(str(ts))}</small></td>
  <td><span class="badge {badge_class}">{_e(level)}</span></td>
  <td>{_e(msg)}</td>
</tr>"""

    tools_str = ", ".join(tools_used) if tools_used else "—"

    return f"""
<section class="report-section">
  <h2>8. Audit-Protokoll</h2>
  <table class="info-table">
    <tr><th>Verwendete Tools</th><td>{_e(tools_str)}</td></tr>
    <tr><th>Protokoll-Einträge</th><td>{len(logs)}</td></tr>
  </table>
  <table class="log-table">
    <thead><tr><th>Zeitstempel</th><th>Level</th><th>Nachricht</th></tr></thead>
    <tbody>{log_rows}</tbody>
  </table>
</section>
"""


def _section_declaration(client_info: Dict, checked_at: str) -> str:
    company = _e(client_info.get("company", "—"))
    return f"""
<section class="report-section declaration">
  <h2>9. Prüfererklärung</h2>
  <p>
    Dieser Bericht wurde durch die automatisierte Prüfplattform
    <strong>{_e(PLATFORM_FULL)}</strong> erstellt und dokumentiert die
    Sicherheitsprüfung der angegebenen Web-Präsenz.
  </p>
  <p>
    Die Prüfung erfolgte auf Basis öffentlich zugänglicher Informationen und
    aktiv übertragener HTTP/TLS-Daten sowie DNS-Einträgen des geprüften Ziels.
    Die Ergebnisse spiegeln den Zustand zum Prüfzeitpunkt wider und erheben
    keinen Anspruch auf Vollständigkeit.
  </p>
  <p>
    Die Empfehlungen basieren auf den Anforderungen der NIS2-Richtlinie
    (Richtlinie (EU) 2022/2555), umgesetzt in §30 BSIG (NIS2UmsuCG),
    sowie der DSGVO (Art. 32) und dem OWASP Top 10.
  </p>
  <table class="info-table">
    <tr><th>Auftraggeber</th><td>{company}</td></tr>
    <tr><th>Prüfdatum</th><td>{_e(checked_at)}</td></tr>
    <tr><th>Auftragnehmer</th><td>{_e(PLATFORM_FULL)}</td></tr>
    <tr><th>Plattform</th><td><a href="{_e(PLATFORM_WEBSITE)}">{_e(PLATFORM_WEBSITE)}</a></td></tr>
  </table>
  <p class="disclaimer">
    <em>
      Dieser Bericht stellt keine Rechtsberatung dar und ersetzt keine
      professionelle Sicherheitsprüfung durch zertifizierte Auditoren.
    </em>
  </p>
</section>
"""


# ---------------------------------------------------------------------------
# CSS styles
# ---------------------------------------------------------------------------
_CSS = """
<style>
  * { box-sizing: border-box; }
  body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 0; color: #2c3e50; background: #fff; }
  .report-container { max-width: 1000px; margin: 0 auto; padding: 20px; }

  /* Cover */
  .cover-page { text-align: center; padding: 60px 40px; border-bottom: 3px solid #2c3e50; margin-bottom: 40px; }
  .platform-brand { font-size: 0.9em; color: #7f8c8d; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 20px; }
  .report-title { font-size: 2.5em; font-weight: 700; color: #2c3e50; margin: 10px 0; line-height: 1.2; }
  .report-subtitle { font-size: 1.1em; color: #7f8c8d; margin-bottom: 30px; }
  .cover-meta { text-align: left; margin: 30px auto; max-width: 600px; }
  .cover-footer { margin-top: 40px; color: #95a5a6; font-size: 0.85em; }

  /* Sections */
  .report-section { margin-bottom: 40px; padding: 0 0 20px 0; border-bottom: 1px solid #ecf0f1; }
  h2 { font-size: 1.6em; color: #2c3e50; border-left: 4px solid #3498db; padding-left: 12px; margin-top: 0; }
  h3 { font-size: 1.2em; color: #34495e; margin-top: 20px; }
  h4 { font-size: 1.05em; color: #2c3e50; margin: 8px 0 4px 0; }
  code { background: #f8f9fa; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; word-break: break-all; }

  /* Tables */
  .meta-table, .info-table, .data-table, .checklist-table, .log-table {
    width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 0.9em;
  }
  .meta-table th, .info-table th, .data-table th, .checklist-table th, .log-table th {
    text-align: left; padding: 8px 12px; background: #f4f6f7; border: 1px solid #dde; width: 200px;
  }
  .meta-table td, .info-table td, .data-table td, .checklist-table td, .log-table td {
    padding: 8px 12px; border: 1px solid #dde; vertical-align: top;
  }
  .data-table th { width: auto; }
  .log-ts { white-space: nowrap; }

  /* Summary cards */
  .summary-grid { display: flex; gap: 16px; margin: 16px 0; flex-wrap: wrap; }
  .summary-card { flex: 1; min-width: 120px; text-align: center; padding: 20px 10px; border-radius: 8px; border: 2px solid; }
  .card-critical { border-color: #c0392b; background: #fdecea; }
  .card-high     { border-color: #e67e22; background: #fef5e7; }
  .card-medium   { border-color: #f39c12; background: #fefde7; }
  .card-low      { border-color: #2980b9; background: #eaf4fb; }
  .card-number { font-size: 2.5em; font-weight: 700; }
  .card-label  { font-size: 0.85em; color: #7f8c8d; margin-top: 4px; }

  /* Findings */
  .finding { margin: 16px 0; padding: 16px; border-radius: 4px; }
  .finding-header { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; font-size: 0.85em; }
  .finding-num { font-weight: 700; color: #7f8c8d; }
  .finding-sev { font-weight: 700; }
  .finding-title { margin: 0 0 8px 0; font-size: 1.05em; }
  .finding-desc { margin: 0 0 8px 0; color: #555; }
  .finding-rec { background: rgba(255,255,255,0.6); padding: 8px; border-radius: 4px; font-size: 0.9em; }
  .cvss, .dsgvo-ref, .finding-tool { background: #eee; padding: 2px 6px; border-radius: 3px; font-size: 0.8em; }

  /* Badges */
  .badge { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.8em; font-weight: 600; }
  .badge-ok    { background: #d4edda; color: #155724; }
  .badge-fail  { background: #f8d7da; color: #721c24; }
  .badge-warn  { background: #fff3cd; color: #856404; }
  .badge-info  { background: #d1ecf1; color: #0c5460; }
  .badge-agent { background: #e2d9f3; color: #4a1f8c; }
  .badge-cmd   { background: #d6eaf8; color: #154360; }

  /* Alerts */
  .alert { padding: 12px 16px; border-radius: 4px; margin: 12px 0; }
  .alert-critical { background: #fdecea; border: 1px solid #c0392b; }
  .alert-high     { background: #fef5e7; border: 1px solid #e67e22; }
  .alert-ok       { background: #d4edda; border: 1px solid #28a745; }

  /* Progress bar */
  .progress-bar { background: #ecf0f1; border-radius: 4px; height: 22px; overflow: hidden; margin: 6px 0; }
  .progress-large { height: 28px; }
  .progress-fill { background: linear-gradient(90deg, #3498db, #2ecc71); height: 100%; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 0.8em; font-weight: 600; min-width: 30px; transition: width 0.3s; }

  /* Checklist */
  .task-done { background: #f0fff4; }
  .task-todo { background: #fff; }
  .no-findings { color: #28a745; font-style: italic; padding: 10px; }

  /* Warning list */
  .warning-list li { color: #856404; }

  /* Log table */
  .log-table { font-size: 0.8em; }

  /* Declaration */
  .declaration { background: #f8f9fa; padding: 20px; border-radius: 4px; }
  .disclaimer { color: #7f8c8d; font-size: 0.85em; }

  /* Print */
  @media print {
    .cover-page { page-break-after: always; }
    .report-section { page-break-inside: avoid; }
    h2 { page-break-after: avoid; }
  }

  /* Navbar (in-app view only) */
  .report-nav { background: #2c3e50; color: #fff; padding: 10px 20px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 0; }
  .report-nav a { color: #ecf0f1; text-decoration: none; margin-left: 12px; }
  .report-nav a:hover { text-decoration: underline; }
  .btn-print { background: #3498db; color: #fff; border: none; padding: 6px 16px; border-radius: 4px; cursor: pointer; font-size: 0.9em; }
</style>
"""


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def generate_report_html(
    target: str,
    client_info: Dict[str, str],
    findings: List[Dict],
    live: Dict,
    tasks: List[Dict],
    logs: Optional[List[Dict]] = None,
    tools_used: Optional[List[str]] = None,
    inline: bool = False,
) -> str:
    """
    Generate a complete HTML report.

    Args:
        target:      Audited URL/domain
        client_info: Dict with keys: company, address, email, phone, ust_id
                     (filled from current_user registration data)
        findings:    List of finding dicts from audit_agent
        live:        Live-check result dict from live_check.py
        tasks:       List of NIS2/DSGVO tasks (with done/notes)
        logs:        Optional list of audit log dicts
        tools_used:  List of tool names that ran
        inline:      If True, return only body HTML (no <html><head> wrapper)

    Returns:
        Complete HTML string
    """
    logs = logs or []
    tools_used = tools_used or []
    checked_at = live.get("checked_at", datetime.utcnow().isoformat())[:19].replace("T", " ")

    body = "\n".join([
        f'<div class="report-container">',
        _section_cover(target, client_info, checked_at),
        _section_summary(findings, tasks, live),
        _section_scope(target, live),
        _section_live_check(live),
        _section_findings(findings),
        _section_checklist(tasks),
        _section_dsgvo(live, findings),
        _section_recommendations(findings),
        _section_protocol(logs, tools_used),
        _section_declaration(client_info, checked_at),
        "</div>",
    ])

    if inline:
        return body

    nav = f"""
<div class="report-nav">
  <span>📋 NIS2 Audit Report — {html.escape(target)}</span>
  <div>
    <button class="btn-print" onclick="window.print()">🖨 Drucken / PDF</button>
    <a href="javascript:history.back()">← Zurück</a>
  </div>
</div>
"""

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NIS2 Audit Report — {html.escape(target)}</title>
  {_CSS}
</head>
<body>
  {nav}
  {body}
</body>
</html>
"""
