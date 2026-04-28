"""
Security Awareness Training — Routes (§30 Abs. 2 Nr. 7 BSIG)

Workflow:
  1. Admin creates training with Markdown content + audience list
  2. System sends personalised email with unique token link to each recipient
  3. Recipient opens link → reads lecture → clicks "Bestätigen"
  4. Acknowledgment (name, timestamp, IP) stored → audit trail for regulator
  5. Admin sees report: who confirmed, who hasn't, exportable for BSI audit
"""

import json
import logging
import secrets
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import (abort, current_app, flash, redirect, render_template,
                   request, url_for)
from services.security_helpers import require_plan
from flask_login import current_user, login_required

from crm.models import db
from ..models import SecurityTraining, TrainingAcknowledgment, TRAINING_TOPICS

logger = logging.getLogger(__name__)

# Default lecture content per topic (Markdown)
DEFAULT_CONTENT = {
    'phishing': """## Phishing & Social Engineering — Pflichtunterweisung

### Was ist Phishing?
Phishing ist der Versuch, über gefälschte E-Mails oder Webseiten sensible Daten zu stehlen.
Angreifer geben sich als Bank, IT-Abteilung oder Vorgesetzter aus.

### Erkennungsmerkmale
- Unbekannter Absender oder leicht abgewandelte Domain (z.B. `microsof t.com`)
- Druck und Dringlichkeit („Ihr Konto wird gesperrt!")
- Links, die auf fremde Domains zeigen (vor dem Klicken hovern!)
- Anhänge von unbekannten Absendern
- Grammatik- und Rechtschreibfehler

### Ihre Pflichten
1. Verdächtige E-Mails **nicht öffnen oder klicken** — an IT-Sicherheit melden
2. Phishing-Versuche über das interne Meldeformular dokumentieren
3. Zugangsdaten **niemals** per E-Mail übermitteln
4. Bei Unsicherheit: Absender telefonisch verifizieren

### Rechtsgrundlage
§30 Abs. 2 Nr. 7 BSIG verpflichtet NIS2-Einrichtungen zur regelmäßigen Schulung aller Mitarbeiter.
Diese Unterweisung ist Teil Ihres Compliance-Programms.""",

    'passwords': """## Sichere Passwörter & Mehrfaktor-Authentifizierung

### Warum sichere Passwörter?
80% aller Datenpannen entstehen durch schwache oder gestohlene Passwörter (Verizon DBIR 2025).

### BSI-Empfehlungen für Passwörter
- Mindestlänge: **12 Zeichen** (empfohlen: 16+)
- Kombination: Groß-/Kleinbuchstaben, Zahlen, Sonderzeichen
- **Keine** Wörter aus dem Wörterbuch
- **Kein** Wiederverwenden von Passwörtern
- Passwort-Manager verwenden (z.B. Bitwarden, KeePass)

### Mehrfaktor-Authentifizierung (MFA)
MFA schützt Accounts auch bei gestohlenem Passwort. Aktivieren Sie MFA für:
- E-Mail-Konto
- VPN-Zugang
- Cloud-Dienste (Microsoft 365, Google Workspace)
- Bankkonto und kritische Systeme

### Passwörter niemals
- Per E-Mail oder Chat teilen
- Auf Notizzetteln aufschreiben
- An Kollegen weitergeben

### Rechtsgrundlage
§30 Abs. 2 Nr. 10 BSIG (MFA) und Nr. 7 (Schulung).""",

    'general': """## Grundlagen der Cybersicherheit — Pflichtunterweisung

### Ihre Rolle in der Cybersicherheit
Jeder Mitarbeiter ist Teil der Sicherheitskette. 95% aller erfolgreichen Angriffe nutzen menschliche Fehler aus (IBM Security Report 2025).

### Die 5 wichtigsten Regeln
1. **Phishing erkennen**: Unbekannte Links und Anhänge nicht öffnen
2. **Passwörter schützen**: Starke, einzigartige Passwörter + MFA aktivieren
3. **Updates installieren**: Betriebssystem und Software aktuell halten
4. **Verdächtiges melden**: Ungewöhnliches sofort der IT-Abteilung melden
5. **Geräte sichern**: Computer beim Verlassen sperren (Win+L / Cmd+Ctrl+Q)

### Was tun bei einem Vorfall?
1. Betroffenes Gerät **sofort vom Netzwerk trennen** (Kabel ziehen / WLAN aus)
2. **Nicht versuchen**, das Problem selbst zu lösen
3. IT-Sicherheit unter der internen Notfallnummer informieren
4. Nichts löschen — Beweise sichern

### Ihre Pflicht nach NIS2
Als Mitarbeiter einer NIS2-regulierten Organisation sind Sie verpflichtet:
- Diese Schulung vollständig zu lesen
- Sicherheitsvorfälle unverzüglich zu melden
- Die interne Sicherheitsrichtlinie einzuhalten

### Rechtsgrundlage
§30 Abs. 2 Nr. 7 BSIG — Schulungen zur Cyberhygiene.""",
}

DEFAULT_CONTENT['ransomware'] = DEFAULT_CONTENT['general']
DEFAULT_CONTENT['data_protection'] = DEFAULT_CONTENT['general']
DEFAULT_CONTENT['remote_work'] = DEFAULT_CONTENT['general']
DEFAULT_CONTENT['social_media'] = DEFAULT_CONTENT['general']
DEFAULT_CONTENT['incident'] = DEFAULT_CONTENT['general']
DEFAULT_CONTENT['access_control'] = DEFAULT_CONTENT['passwords']
DEFAULT_CONTENT['cloud_security'] = DEFAULT_CONTENT['general']


def register_training_routes(bp):

    # ── List ──────────────────────────────────────────────────────
    @bp.route('/training/')
    @login_required
    @require_plan("professional")
    def training_list():
        trainings = SecurityTraining.query.filter_by(user_id=current_user.id)\
            .order_by(SecurityTraining.created_at.desc()).all()
        return render_template('nis2/training/list.html',
                               trainings=trainings,
                               topics=dict(TRAINING_TOPICS))

    # ── Create ────────────────────────────────────────────────────
    @bp.route('/training/create', methods=['GET', 'POST'])
    @login_required
    @require_plan("professional")
    def training_create():
        if request.method == 'POST':
            topic = request.form.get('topic', 'general')
            title = request.form.get('title', '').strip()
            content_md = request.form.get('content_md', '').strip()
            summary = request.form.get('summary', '').strip()
            due_date_str = request.form.get('due_date', '')

            # Parse audience: one per line — "Name <email>" or just "email"
            raw_audience = request.form.get('audience', '')
            audience = _parse_audience(raw_audience)

            if not title:
                flash('Bitte einen Titel angeben.', 'danger')
                return redirect(url_for('nis2.training_create'))
            if not content_md:
                flash('Inhalt darf nicht leer sein.', 'danger')
                return redirect(url_for('nis2.training_create'))

            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass

            training = SecurityTraining(
                user_id=current_user.id,
                title=title,
                topic=topic,
                content_md=content_md,
                summary=summary or None,
                due_date=due_date,
                status='draft',
            )
            training.set_audience(audience)
            db.session.add(training)
            db.session.commit()

            flash('Schulung erstellt.', 'success')
            return redirect(url_for('nis2.training_detail', training_id=training.id))

        # Pre-fill content based on topic param
        prefill_topic = request.args.get('topic', 'general')
        prefill_content = DEFAULT_CONTENT.get(prefill_topic, DEFAULT_CONTENT['general'])

        # Load TeamGuard members as audience suggestions
        team_members = _get_team_members()

        return render_template('nis2/training/create.html',
                               topics=TRAINING_TOPICS,
                               prefill_content=prefill_content,
                               prefill_topic=prefill_topic,
                               team_members=team_members)

    # ── Detail / management view ──────────────────────────────────
    @bp.route('/training/<int:training_id>')
    @login_required
    @require_plan("professional")
    def training_detail(training_id):
        training = SecurityTraining.query.filter_by(
            id=training_id, user_id=current_user.id
        ).first_or_404()
        acks = training.acknowledgments.order_by(
            TrainingAcknowledgment.sent_at.asc()
        ).all()
        return render_template('nis2/training/detail.html',
                               training=training,
                               acks=acks,
                               topics=dict(TRAINING_TOPICS))

    # ── Send to audience ──────────────────────────────────────────
    @bp.route('/training/<int:training_id>/send', methods=['POST'])
    @login_required
    @require_plan("professional")
    def training_send(training_id):
        training = SecurityTraining.query.filter_by(
            id=training_id, user_id=current_user.id
        ).first_or_404()

        audience = training.get_audience()
        if not audience:
            flash('Keine Empfänger angegeben.', 'warning')
            return redirect(url_for('nis2.training_detail', training_id=training_id))

        sent_count = 0
        error_count = 0

        for person in audience:
            name = person.get('name', '')
            email = person.get('email', '')
            if not email:
                continue

            # Check if already sent to this email
            existing = TrainingAcknowledgment.query.filter_by(
                training_id=training_id, recipient_email=email
            ).first()
            if existing:
                continue  # Skip re-send

            token = secrets.token_urlsafe(32)
            ack = TrainingAcknowledgment(
                training_id=training_id,
                recipient_name=name or email,
                recipient_email=email,
                token=token,
            )
            db.session.add(ack)
            db.session.flush()  # get ID

            ok = _send_training_email(training, name or email, email, token)
            if ok:
                sent_count += 1
            else:
                error_count += 1

        training.status = 'sent'
        training.sent_at = datetime.utcnow()
        db.session.commit()

        if sent_count:
            flash(f'Schulung an {sent_count} Empfänger versendet.', 'success')
        if error_count:
            flash(f'{error_count} E-Mails konnten nicht zugestellt werden (SMTP-Fehler).', 'warning')

        return redirect(url_for('nis2.training_detail', training_id=training_id))

    # ── Resend to single recipient ────────────────────────────────
    @bp.route('/training/<int:training_id>/resend/<int:ack_id>', methods=['POST'])
    @login_required
    @require_plan("professional")
    def training_resend(training_id, ack_id):
        training = SecurityTraining.query.filter_by(
            id=training_id, user_id=current_user.id
        ).first_or_404()
        ack = TrainingAcknowledgment.query.filter_by(
            id=ack_id, training_id=training_id
        ).first_or_404()

        ok = _send_training_email(
            training, ack.recipient_name, ack.recipient_email, ack.token
        )
        if ok:
            flash(f'Erinnerung an {ack.recipient_email} gesendet.', 'success')
        else:
            flash('E-Mail-Versand fehlgeschlagen — SMTP prüfen.', 'danger')
        return redirect(url_for('nis2.training_detail', training_id=training_id))

    # ── Acknowledgment page (public — no login required) ──────────
    @bp.route('/training/ack/<token>', methods=['GET', 'POST'])
    def training_ack(token):
        ack = TrainingAcknowledgment.query.filter_by(token=token).first_or_404()
        training = SecurityTraining.query.get_or_404(ack.training_id)

        # Record first open
        if not ack.opened_at:
            ack.opened_at = datetime.utcnow()
            db.session.commit()

        if request.method == 'POST':
            if ack.acknowledged:
                flash('Sie haben diese Schulung bereits bestätigt.', 'info')
                return render_template('nis2/training/ack.html',
                                       ack=ack, training=training, already_done=True)

            confirmed_name = request.form.get('confirmed_name', '').strip()
            if not confirmed_name:
                flash('Bitte geben Sie Ihren vollständigen Namen ein.', 'danger')
                return render_template('nis2/training/ack.html',
                                       ack=ack, training=training)

            # Get real IP (behind proxy)
            ip = (request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
                  or request.remote_addr or '')
            # Limit to 45 chars (IPv6 max)
            ip = ip[:45]

            ack.acknowledged = True
            ack.acknowledged_at = datetime.utcnow()
            ack.confirmed_name = confirmed_name
            ack.ip_address = ip
            db.session.commit()

            return render_template('nis2/training/ack_done.html',
                                   ack=ack, training=training)

        return render_template('nis2/training/ack.html',
                               ack=ack, training=training)

    # ── Compliance report (for auditor / BSI) ─────────────────────
    @bp.route('/training/<int:training_id>/report')
    @login_required
    @require_plan("professional")
    def training_report(training_id):
        training = SecurityTraining.query.filter_by(
            id=training_id, user_id=current_user.id
        ).first_or_404()
        acks = training.acknowledgments.order_by(
            TrainingAcknowledgment.acknowledged.desc(),
            TrainingAcknowledgment.acknowledged_at.asc(),
        ).all()
        return render_template('nis2/training/report.html',
                               training=training,
                               acks=acks,
                               now=datetime.utcnow(),
                               topics=dict(TRAINING_TOPICS))

    # ── Delete (draft only) ───────────────────────────────────────
    @bp.route('/training/<int:training_id>/delete', methods=['POST'])
    @login_required
    @require_plan("professional")
    def training_delete(training_id):
        training = SecurityTraining.query.filter_by(
            id=training_id, user_id=current_user.id
        ).first_or_404()
        if training.status != 'draft':
            flash('Nur Entwürfe können gelöscht werden.', 'warning')
            return redirect(url_for('nis2.training_detail', training_id=training_id))
        db.session.delete(training)
        db.session.commit()
        flash('Schulung gelöscht.', 'success')
        return redirect(url_for('nis2.training_list'))


# ── Helpers ───────────────────────────────────────────────────────

def _get_team_members():
    """Return TeamGuard members for the current user, if any."""
    try:
        from app.teamguard.models import TeamMember
        return TeamMember.query.filter_by(
            owner_user_id=current_user.id, is_active=True
        ).order_by(TeamMember.full_name).all()
    except Exception:
        return []


def _parse_audience(raw: str) -> list:
    """
    Parse textarea input into list of {name, email}.
    Supports formats:
      - max@example.com
      - Max Mustermann <max@example.com>
      - max@example.com; Max Mustermann
    One entry per line.
    """
    import re
    result = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # "Name <email>" format
        m = re.match(r'^(.+?)\s*<([^>]+)>\s*$', line)
        if m:
            result.append({'name': m.group(1).strip(), 'email': m.group(2).strip().lower()})
            continue
        # "email; Name" format
        if ';' in line:
            parts = [p.strip() for p in line.split(';', 1)]
            email = parts[0].lower()
            name = parts[1] if len(parts) > 1 else ''
            result.append({'name': name, 'email': email})
            continue
        # Just email
        if '@' in line:
            result.append({'name': '', 'email': line.lower()})
    return result


def _send_training_email(training: SecurityTraining,
                          recipient_name: str,
                          recipient_email: str,
                          token: str) -> bool:
    """Send acknowledgment link email via SMTP."""
    try:
        smtp_server = current_app.config.get('MAIL_SERVER')
        smtp_port = int(current_app.config.get('MAIL_PORT', 587))
        smtp_user = current_app.config.get('MAIL_USERNAME')
        smtp_pass = current_app.config.get('MAIL_PASSWORD')
        mail_sender = current_app.config.get('MAIL_DEFAULT_SENDER', smtp_user)

        if not all([smtp_server, smtp_user, smtp_pass, mail_sender]):
            logger.warning('Training email: SMTP not configured — skipping')
            return False

        ack_url = url_for('nis2.training_ack', token=token, _external=True)
        due_str = training.due_date.strftime('%d.%m.%Y') if training.due_date else '–'

        subject = f'[Pflichtschulung] {training.title}'

        text_body = (
            f'Hallo {recipient_name},\n\n'
            f'Sie werden gebeten, die folgende Pflichtschulung bis {due_str} zu lesen '
            f'und Ihre Kenntnisnahme zu bestätigen:\n\n'
            f'📋 {training.title}\n\n'
            f'Bitte klicken Sie auf den folgenden Link:\n{ack_url}\n\n'
            f'Nach dem Lesen bestätigen Sie mit Ihrem Namen — es dauert ca. 3-5 Minuten.\n\n'
            f'Mit freundlichen Grüßen\nIhr Sicherheitsteam'
        )
        html_body = f"""
<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto;color:#333">
<div style="background:#1a56db;padding:20px;border-radius:8px 8px 0 0">
  <h2 style="color:white;margin:0">🛡️ Pflichtschulung: Cybersicherheit</h2>
</div>
<div style="padding:24px;background:#f9fafb;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 8px 8px">
  <p>Hallo <strong>{recipient_name}</strong>,</p>
  <p>Sie werden gebeten, folgende <strong>Pflichtunterweisung</strong> bis
     <strong>{due_str}</strong> zu lesen und zu bestätigen:</p>
  <div style="background:white;border-left:4px solid #1a56db;padding:12px 16px;margin:16px 0;border-radius:4px">
    <strong>📋 {training.title}</strong>
  </div>
  <p>Nach dem Lesen geben Sie bitte Ihren Namen als Bestätigung ein.
     Das dauert ca. 3–5 Minuten.</p>
  <div style="text-align:center;margin:24px 0">
    <a href="{ack_url}"
       style="background:#1a56db;color:white;padding:14px 28px;border-radius:6px;
              text-decoration:none;font-weight:bold;font-size:16px">
      📖 Schulung lesen &amp; bestätigen
    </a>
  </div>
  <p style="font-size:12px;color:#6b7280">
    Dieser Link ist personalisiert und gilt nur für {recipient_email}.<br>
    Grundlage: §30 Abs. 2 Nr. 7 BSIG (NIS2-Richtlinie).
  </p>
</div>
</body></html>"""

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = mail_sender
        msg['To'] = recipient_email
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True

    except Exception as e:
        logger.error(f'Training email send failed to {recipient_email}: {e}', exc_info=True)
        return False
