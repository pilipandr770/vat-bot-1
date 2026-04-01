"""
TeamGuard Views — Team security management routes.
Blueprint prefix: /teamguard/
"""

import hashlib
import os
import secrets
import string
from datetime import datetime, timedelta

from flask import (Blueprint, abort, current_app, flash, jsonify, redirect,
                   render_template, request, url_for)
from flask_login import current_user, login_required

from crm.models import db

teamguard_bp = Blueprint('teamguard', __name__, url_prefix='/teamguard')


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _generate_secure_password(length: int = 16, require_upper=True,
                               require_digit=True, require_special=True) -> str:
    """Generate a cryptographically secure random password."""
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase if require_upper else ''
    digits = string.digits if require_digit else ''
    special = '!@#$%^&*()-_=+[]{}' if require_special else ''
    alphabet = lower + upper + digits + special

    # Guarantee at least one of each required character class
    required = [secrets.choice(lower)]
    if require_upper:
        required.append(secrets.choice(upper))
    if require_digit:
        required.append(secrets.choice(digits))
    if require_special:
        required.append(secrets.choice(special))

    remaining = [secrets.choice(alphabet) for _ in range(length - len(required))]
    password_chars = required + remaining
    # Shuffle to avoid predictable character positions
    secrets.SystemRandom().shuffle(password_chars)
    return ''.join(password_chars)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def _send_password_email(member, new_password: str, admin_email: str):
    """
    Send generated password to team member via Flask-Mail / SMTP.
    Returns True on success, False if email sending is unavailable.
    """
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        smtp_server = os.environ.get('SMTP_SERVER')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        smtp_user = os.environ.get('SMTP_USERNAME')
        smtp_pass = os.environ.get('SMTP_PASSWORD')
        sender = os.environ.get('MAIL_DEFAULT_SENDER', smtp_user)

        if not all([smtp_server, smtp_user, smtp_pass, sender]):
            current_app.logger.warning('TeamGuard: SMTP not configured, cannot send password email')
            return False

        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Ihr neues sicheres Passwort — VAT Verifizierung TeamGuard'
        msg['From'] = sender
        msg['To'] = member.email

        html_body = f"""
        <html><body>
        <p>Hallo <strong>{member.full_name}</strong>,</p>
        <p>Ihr Administrator hat ein neues sicheres Passwort für Ihr Konto generiert.</p>
        <p style="background:#f5f5f5;padding:12px;font-size:1.2em;font-family:monospace;
                  border-left:4px solid #007bff;">
            <strong>Neues Passwort:</strong> {new_password}
        </p>
        <p><strong>Wichtig:</strong></p>
        <ul>
          <li>Ändern Sie dieses Passwort nach der ersten Anmeldung sofort.</li>
          <li>Speichern Sie es nur in einem Passwort-Manager (z.B. Bitwarden, 1Password).</li>
          <li>Teilen Sie dieses Passwort niemals mit anderen Personen.</li>
        </ul>
        <p>Bei Fragen wenden Sie sich an: <a href="mailto:{admin_email}">{admin_email}</a></p>
        <hr>
        <small>Diese E-Mail wurde automatisch von VAT Verifizierung TeamGuard generiert.</small>
        </body></html>
        """

        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        return True
    except Exception as e:
        current_app.logger.error(f'TeamGuard: password email failed: {e}', exc_info=True)
        return False


def _send_team_message_email(member, subject: str, body: str, sender_email: str):
    """Send a free-form message to a team member."""
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        smtp_server = os.environ.get('SMTP_SERVER')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        smtp_user = os.environ.get('SMTP_USERNAME')
        smtp_pass = os.environ.get('SMTP_PASSWORD')
        mail_sender = os.environ.get('MAIL_DEFAULT_SENDER', smtp_user)

        if not all([smtp_server, smtp_user, smtp_pass, mail_sender]):
            return False

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = mail_sender
        msg['Reply-To'] = sender_email
        msg['To'] = member.email

        text_body = body
        html_body = f"""
        <html><body>
        <p>Hallo <strong>{member.full_name}</strong>,</p>
        <div style="white-space:pre-wrap">{body}</div>
        <hr>
        <small>Gesendet über VAT Verifizierung TeamGuard</small>
        </body></html>
        """
        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        current_app.logger.error(f'TeamGuard: message email failed: {e}', exc_info=True)
        return False


def _log_event(member_id, owner_user_id, event_type, description=None, performed_by=None):
    from app.teamguard.models import SecurityEvent
    ev = SecurityEvent(
        member_id=member_id,
        owner_user_id=owner_user_id,
        event_type=event_type,
        description=description,
        performed_by=performed_by or current_user.email,
    )
    db.session.add(ev)


# ─── Dashboard ────────────────────────────────────────────────────────────────

@teamguard_bp.route('/')
@login_required
def dashboard():
    from app.teamguard.models import (TeamMember, PasswordPolicy, SecurityEvent,
                                       PhishingTest, EVENT_TYPE_LABELS)

    members = TeamMember.query.filter_by(
        owner_user_id=current_user.id, is_active=True
    ).order_by(TeamMember.full_name).all()

    policy = PasswordPolicy.query.filter_by(owner_user_id=current_user.id).first()
    rotation_days = policy.rotation_days if policy else 90

    # Members with expired or no password record
    expired = [m for m in members if m.password_expired]
    no_record = [m for m in members if m.password_last_changed is None]

    # Recent events (last 20)
    recent_events = (
        SecurityEvent.query
        .filter_by(owner_user_id=current_user.id)
        .order_by(SecurityEvent.created_at.desc())
        .limit(20)
        .all()
    )

    active_phishing = PhishingTest.query.filter_by(
        owner_user_id=current_user.id, status='sent'
    ).all()

    return render_template(
        'teamguard/dashboard.html',
        members=members,
        policy=policy,
        rotation_days=rotation_days,
        expired_members=expired,
        no_record_members=no_record,
        recent_events=recent_events,
        active_phishing=active_phishing,
        event_labels=EVENT_TYPE_LABELS,
    )


# ─── Team Members ─────────────────────────────────────────────────────────────

@teamguard_bp.route('/team')
@login_required
def team_list():
    from app.teamguard.models import TeamMember, ACCESS_LEVEL_LABELS, PasswordPolicy

    members = TeamMember.query.filter_by(
        owner_user_id=current_user.id
    ).order_by(TeamMember.is_active.desc(), TeamMember.full_name).all()

    policy = PasswordPolicy.query.filter_by(owner_user_id=current_user.id).first()
    rotation_days = policy.rotation_days if policy else 90

    return render_template(
        'teamguard/team_list.html',
        members=members,
        rotation_days=rotation_days,
        access_labels=ACCESS_LEVEL_LABELS,
    )


@teamguard_bp.route('/team/add', methods=['GET', 'POST'])
@login_required
def add_member():
    from app.teamguard.models import TeamMember, ACCESS_LEVELS, ACCESS_LEVEL_LABELS

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        position = request.form.get('position', '').strip()
        access_level = request.form.get('access_level', 'employee')
        notes = request.form.get('notes', '').strip()

        if not full_name or not email:
            flash('Name und E-Mail sind Pflichtfelder.', 'danger')
            return redirect(url_for('teamguard.add_member'))
        if access_level not in ACCESS_LEVELS:
            flash('Ungültige Zugriffsebene.', 'danger')
            return redirect(url_for('teamguard.add_member'))

        # Check duplicate email within same owner
        existing = TeamMember.query.filter_by(
            owner_user_id=current_user.id, email=email
        ).first()
        if existing:
            flash(f'Ein Mitglied mit dieser E-Mail existiert bereits.', 'warning')
            return redirect(url_for('teamguard.add_member'))

        member = TeamMember(
            owner_user_id=current_user.id,
            full_name=full_name,
            email=email,
            position=position,
            access_level=access_level,
            notes=notes,
        )
        db.session.add(member)
        db.session.flush()  # get member.id before event log

        _log_event(member.id, current_user.id, 'onboarding',
                   description=f'Mitarbeiter {full_name} hinzugefügt')
        db.session.commit()

        flash(f'{full_name} wurde erfolgreich hinzugefügt.', 'success')
        return redirect(url_for('teamguard.team_list'))

    return render_template(
        'teamguard/add_member.html',
        access_levels=ACCESS_LEVELS,
        access_labels=ACCESS_LEVEL_LABELS,
    )


@teamguard_bp.route('/team/<int:member_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_member(member_id):
    from app.teamguard.models import TeamMember, ACCESS_LEVELS, ACCESS_LEVEL_LABELS

    member = TeamMember.query.filter_by(
        id=member_id, owner_user_id=current_user.id
    ).first_or_404()

    if request.method == 'POST':
        old_level = member.access_level
        member.full_name = request.form.get('full_name', member.full_name).strip()
        member.position = request.form.get('position', '').strip()
        member.notes = request.form.get('notes', '').strip()
        new_level = request.form.get('access_level', member.access_level)
        if new_level in ACCESS_LEVELS:
            member.access_level = new_level
        member.password_rotation_days = request.form.get('password_rotation_days') or None
        if member.password_rotation_days:
            member.password_rotation_days = int(member.password_rotation_days)

        if old_level != member.access_level:
            _log_event(member.id, current_user.id, 'access_changed',
                       description=f'Zugriffsebene geändert: {old_level} → {member.access_level}')

        db.session.commit()
        flash('Mitarbeiterdaten gespeichert.', 'success')
        return redirect(url_for('teamguard.team_list'))

    return render_template(
        'teamguard/edit_member.html',
        member=member,
        access_levels=ACCESS_LEVELS,
        access_labels=ACCESS_LEVEL_LABELS,
    )


@teamguard_bp.route('/team/<int:member_id>/deactivate', methods=['POST'])
@login_required
def deactivate_member(member_id):
    from app.teamguard.models import TeamMember

    member = TeamMember.query.filter_by(
        id=member_id, owner_user_id=current_user.id
    ).first_or_404()

    member.is_active = False
    _log_event(member.id, current_user.id, 'offboarding',
               description=f'Mitarbeiter deaktiviert (Offboarding): {member.full_name}')
    db.session.commit()
    flash(f'{member.full_name} wurde deaktiviert. Vergessen Sie nicht, alle System-Zugänge zu sperren!',
          'warning')
    return redirect(url_for('teamguard.team_list'))


# ─── Password Management ──────────────────────────────────────────────────────

@teamguard_bp.route('/team/<int:member_id>/send-password', methods=['POST'])
@login_required
def send_password(member_id):
    from app.teamguard.models import TeamMember, PasswordAssignment, PasswordPolicy

    member = TeamMember.query.filter_by(
        id=member_id, owner_user_id=current_user.id
    ).first_or_404()

    policy = PasswordPolicy.query.filter_by(owner_user_id=current_user.id).first()
    min_len = policy.min_length if policy else 16
    req_upper = policy.require_uppercase if policy else True
    req_digit = policy.require_digit if policy else True
    req_special = policy.require_special if policy else True

    new_password = _generate_secure_password(
        length=max(min_len, 12),
        require_upper=req_upper,
        require_digit=req_digit,
        require_special=req_special,
    )

    success = _send_password_email(member, new_password, current_user.email)

    if success:
        # Record assignment (hash only — never store plaintext)
        assignment = PasswordAssignment(
            member_id=member.id,
            password_hash=_hash_password(new_password),
            sent_by_user_id=current_user.id,
        )
        db.session.add(assignment)

        # Update member's password change date
        member.password_last_changed = datetime.utcnow()

        _log_event(member.id, current_user.id, 'password_reset',
                   description=f'Sicheres Passwort generiert und per E-Mail gesendet an {member.email}')
        db.session.commit()

        flash(f'Sicheres Passwort wurde an {member.email} gesendet.', 'success')
    else:
        flash('E-Mail konnte nicht gesendet werden. Bitte SMTP-Konfiguration prüfen.', 'danger')

    return redirect(url_for('teamguard.team_list'))


@teamguard_bp.route('/team/send-password-bulk', methods=['POST'])
@login_required
def send_password_bulk():
    """Send new passwords to all members with expired or missing passwords."""
    from app.teamguard.models import TeamMember, PasswordAssignment, PasswordPolicy

    policy = PasswordPolicy.query.filter_by(owner_user_id=current_user.id).first()
    rotation_days = policy.rotation_days if policy else 90
    min_len = policy.min_length if policy else 16

    members_to_reset = TeamMember.query.filter_by(
        owner_user_id=current_user.id, is_active=True
    ).all()
    targets = [m for m in members_to_reset if m.password_expired or m.password_last_changed is None]

    sent_count = 0
    for member in targets:
        new_password = _generate_secure_password(length=max(min_len, 12))
        if _send_password_email(member, new_password, current_user.email):
            assignment = PasswordAssignment(
                member_id=member.id,
                password_hash=_hash_password(new_password),
                sent_by_user_id=current_user.id,
            )
            db.session.add(assignment)
            member.password_last_changed = datetime.utcnow()
            _log_event(member.id, current_user.id, 'password_reset',
                       description='Bulk-Passwort-Reset')
            sent_count += 1

    db.session.commit()
    flash(f'Neue Passwörter wurden an {sent_count} Mitarbeiter gesendet.', 'success')
    return redirect(url_for('teamguard.dashboard'))


# ─── Password Policy ──────────────────────────────────────────────────────────

@teamguard_bp.route('/policy', methods=['GET', 'POST'])
@login_required
def password_policy():
    from app.teamguard.models import PasswordPolicy

    policy = PasswordPolicy.query.filter_by(owner_user_id=current_user.id).first()

    if request.method == 'POST':
        rotation_days = int(request.form.get('rotation_days', 90))
        min_length = max(8, int(request.form.get('min_length', 12)))
        require_uppercase = 'require_uppercase' in request.form
        require_digit = 'require_digit' in request.form
        require_special = 'require_special' in request.form
        reminder_days = int(request.form.get('reminder_days_before', 7))

        if not policy:
            policy = PasswordPolicy(owner_user_id=current_user.id)
            db.session.add(policy)

        policy.rotation_days = rotation_days
        policy.min_length = min_length
        policy.require_uppercase = require_uppercase
        policy.require_digit = require_digit
        policy.require_special = require_special
        policy.reminder_days_before = reminder_days
        db.session.commit()

        flash('Passwort-Richtlinie gespeichert.', 'success')
        return redirect(url_for('teamguard.password_policy'))

    return render_template('teamguard/password_policy.html', policy=policy)


# ─── Team Messaging ───────────────────────────────────────────────────────────

@teamguard_bp.route('/message', methods=['GET', 'POST'])
@login_required
def send_message():
    from app.teamguard.models import TeamMember

    members = TeamMember.query.filter_by(
        owner_user_id=current_user.id, is_active=True
    ).order_by(TeamMember.full_name).all()

    if request.method == 'POST':
        recipient_ids = request.form.getlist('recipient_ids')
        subject = request.form.get('subject', '').strip()
        body = request.form.get('body', '').strip()

        if not subject or not body or not recipient_ids:
            flash('Betreff, Nachricht und mindestens ein Empfänger sind erforderlich.', 'danger')
            return redirect(url_for('teamguard.send_message'))

        sent = 0
        for mid in recipient_ids:
            member = TeamMember.query.filter_by(
                id=int(mid), owner_user_id=current_user.id
            ).first()
            if member:
                ok = _send_team_message_email(member, subject, body, current_user.email)
                if ok:
                    _log_event(member.id, current_user.id, 'message_sent',
                               description=f'Betreff: {subject[:100]}')
                    sent += 1

        db.session.commit()
        flash(f'Nachricht an {sent} Mitarbeiter gesendet.', 'success')
        return redirect(url_for('teamguard.dashboard'))

    return render_template('teamguard/send_message.html', members=members)


# ─── Phishing Simulation ──────────────────────────────────────────────────────

@teamguard_bp.route('/phishing')
@login_required
def phishing_list():
    from app.teamguard.models import PhishingTest

    tests = PhishingTest.query.filter_by(
        owner_user_id=current_user.id
    ).order_by(PhishingTest.created_at.desc()).all()

    return render_template('teamguard/phishing_list.html', tests=tests)


@teamguard_bp.route('/phishing/create', methods=['GET', 'POST'])
@login_required
def create_phishing_test():
    from app.teamguard.models import TeamMember, PhishingTest

    members = TeamMember.query.filter_by(
        owner_user_id=current_user.id, is_active=True
    ).order_by(TeamMember.full_name).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        subject_line = request.form.get('subject_line', '').strip()
        template_type = request.form.get('template_type', 'link_click')
        recipient_ids = request.form.getlist('recipient_ids')

        if not name or not subject_line or not recipient_ids:
            flash('Alle Pflichtfelder ausfüllen und mindestens einen Empfänger wählen.', 'danger')
            return redirect(url_for('teamguard.create_phishing_test'))

        token = secrets.token_urlsafe(32)
        test = PhishingTest(
            owner_user_id=current_user.id,
            name=name,
            subject_line=subject_line,
            template_type=template_type,
            tracking_token=token,
            status='draft',
        )
        test.sent_to_member_ids = [int(mid) for mid in recipient_ids]
        db.session.add(test)
        db.session.commit()

        flash(f'Phishing-Test "{name}" erstellt. Jetzt versenden?', 'info')
        return redirect(url_for('teamguard.phishing_detail', test_id=test.id))

    return render_template('teamguard/create_phishing_test.html', members=members)


@teamguard_bp.route('/phishing/<int:test_id>')
@login_required
def phishing_detail(test_id):
    from app.teamguard.models import PhishingTest, TeamMember, PhishingClick

    test = PhishingTest.query.filter_by(
        id=test_id, owner_user_id=current_user.id
    ).first_or_404()

    member_ids = test.sent_to_member_ids
    members_map = {
        m.id: m for m in TeamMember.query.filter(
            TeamMember.id.in_(member_ids)
        ).all()
    } if member_ids else {}

    clicked_ids = {c.member_id for c in test.clicks.all()}

    tracking_url = url_for('teamguard.phishing_track',
                           token=test.tracking_token, _external=True)

    return render_template(
        'teamguard/phishing_detail.html',
        test=test,
        members_map=members_map,
        clicked_ids=clicked_ids,
        tracking_url=tracking_url,
    )


@teamguard_bp.route('/phishing/<int:test_id>/send', methods=['POST'])
@login_required
def send_phishing_test(test_id):
    from app.teamguard.models import PhishingTest, TeamMember

    test = PhishingTest.query.filter_by(
        id=test_id, owner_user_id=current_user.id
    ).first_or_404()

    if test.status != 'draft':
        flash('Dieser Test wurde bereits versendet.', 'warning')
        return redirect(url_for('teamguard.phishing_detail', test_id=test_id))

    tracking_url = url_for('teamguard.phishing_track',
                           token=test.tracking_token, _external=True)

    sent = 0
    for mid in test.sent_to_member_ids:
        member = TeamMember.query.filter_by(
            id=mid, owner_user_id=current_user.id
        ).first()
        if not member:
            continue

        # Send a realistic-looking phishing simulation email
        subject = test.subject_line
        html_body = f"""
        <html><body>
        <p>Hallo {member.full_name},</p>
        <p>Bitte überprüfen Sie die folgende wichtige Sicherheitsmeldung sofort:</p>
        <p><a href="{tracking_url}?m={mid}" style="color:#d9534f;font-weight:bold;">
           ⚠️ Sicherheitswarnung: Jetzt prüfen →
        </a></p>
        <p>Falls Sie Fragen haben, kontaktieren Sie Ihren IT-Administrator.</p>
        <hr><small>Diese Nachricht ist Teil eines internen Sicherheitstest-Programms.</small>
        </body></html>
        """

        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            smtp_server = os.environ.get('SMTP_SERVER')
            smtp_port = int(os.environ.get('SMTP_PORT', 587))
            smtp_user = os.environ.get('SMTP_USERNAME')
            smtp_pass = os.environ.get('SMTP_PASSWORD')
            mail_sender = os.environ.get('MAIL_DEFAULT_SENDER', smtp_user)

            if smtp_server and smtp_user and smtp_pass:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = mail_sender
                msg['To'] = member.email
                msg.attach(MIMEText(html_body, 'html'))

                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                    server.send_message(msg)
                sent += 1
        except Exception as e:
            current_app.logger.error(f'Phishing send failed for member {mid}: {e}')

    test.status = 'sent'
    test.sent_at = datetime.utcnow()
    db.session.commit()

    flash(f'Phishing-Test an {sent} Mitarbeiter gesendet.', 'success')
    return redirect(url_for('teamguard.phishing_detail', test_id=test_id))


@teamguard_bp.route('/phishing/track/<token>')
def phishing_track(token):
    """
    Tracking endpoint — called when a member clicks the phishing test link.
    Does NOT require login (it's the fake phishing landing page).

    SECURITY: Only records clicks for existing, active tests owned by registered admins.
    No personal data is stored beyond member_id and a hashed IP.
    """
    from app.teamguard.models import PhishingTest, PhishingClick, TeamMember, SecurityEvent

    test = PhishingTest.query.filter_by(tracking_token=token, status='sent').first()
    if not test:
        # Invalid/expired token — show generic security awareness page
        return render_template('teamguard/phishing_landed.html',
                               test=None, member=None, already_clicked=True)

    member_id = request.args.get('m', type=int)
    member = None
    already_clicked = False

    if member_id:
        # Validate member belongs to this test's owner
        member = TeamMember.query.filter_by(
            id=member_id, owner_user_id=test.owner_user_id
        ).first()

        if member:
            # Idempotent: only record first click
            existing = PhishingClick.query.filter_by(
                test_id=test.id, member_id=member_id
            ).first()
            if not existing:
                raw_ip = request.remote_addr or ''
                click = PhishingClick(
                    test_id=test.id,
                    member_id=member_id,
                    ip_hash=hashlib.sha256(raw_ip.encode()).hexdigest(),
                    user_agent_snippet=(request.user_agent.string or '')[:200],
                )
                db.session.add(click)

                    # Log security event directly (avoid importing self)
                    sec_ev = SecurityEvent(
                        member_id=member_id,
                        owner_user_id=test.owner_user_id,
                        event_type='phishing_click',
                        description=f'Hat Phishing-Test "{test.name}" angeklickt',
# ─── Security Events Log ──────────────────────────────────────────────────────

@teamguard_bp.route('/events')
@login_required
def event_log():
    from app.teamguard.models import SecurityEvent, TeamMember, EVENT_TYPE_LABELS

    page = request.args.get('page', 1, type=int)
    events = (
        SecurityEvent.query
        .filter_by(owner_user_id=current_user.id)
        .order_by(SecurityEvent.created_at.desc())
        .paginate(page=page, per_page=50, error_out=False)
    )

    member_ids = {e.member_id for e in events.items}
    members_map = {m.id: m for m in TeamMember.query.filter(
        TeamMember.id.in_(member_ids)
    ).all()} if member_ids else {}

    return render_template(
        'teamguard/event_log.html',
        events=events,
        members_map=members_map,
        event_labels=EVENT_TYPE_LABELS,
    )
