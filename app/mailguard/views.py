from flask import (
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    flash,
    current_app,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import json
import os
import requests
from datetime import datetime, timedelta

from . import mailguard_bp
from .models import (
    db,
    MailAccount,
    KnownCounterparty,
    MailRule,
    MailMessage,
    MailDraft,
    ScanReport,
)
from .tasks import sync_imap_account
from .oauth import encrypt_token
from .rules import create_default_rules
import json

@mailguard_bp.route('/')
@login_required
def dashboard():
    """Главная страница MailGuard"""
    # Получаем подключенные аккаунты
    accounts = MailAccount.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    # Получаем активные правила
    rules = MailRule.query.filter_by(is_enabled=True).order_by(MailRule.priority.desc()).all()

    # Получаем черновики ожидающие подтверждения
    pending_drafts = MailDraft.query.join(MailMessage).join(MailAccount)\
        .filter(MailAccount.user_id == current_user.id)\
        .filter(MailDraft.approved_by_user == False)\
        .filter(MailDraft.sent_at.is_(None))\
        .order_by(MailDraft.created_at.desc())\
        .limit(10).all()

    # Получаем последние сообщения
    recent_messages = MailMessage.query.join(MailAccount)\
        .filter(MailAccount.user_id == current_user.id)\
        .order_by(MailMessage.received_at.desc())\
        .limit(20).all()

    security_counts = {'safe': 0, 'warning': 0, 'blocked': 0, 'review': 0}
    flagged_messages = []

    for message in recent_messages:
        security = message.get_security_meta() or {}
        status = security.get('status') or ('blocked' if message.is_quarantined else 'review')
        if status not in security_counts:
            security_counts[status] = 0
        security_counts[status] += 1

        if status in ('warning', 'blocked', 'review'):
            flagged_messages.append({
                'id': message.id,
                'subject': message.subject or '(без темы)',
                'from_email': message.from_email,
                'received_at': message.received_at,
                'status': status,
                'status_label': security.get('status_label', status.title()),
                'flag_color': security.get('flag_color', 'secondary'),
                'summary': security.get('summary'),
                'score': security.get('score'),
                'checked_at_display': security.get('checked_at_display')
            })

    security_overview = {
        'counts': security_counts,
        'flagged': flagged_messages[:6]
    }
    
    # Статистика
    today = datetime.utcnow().date()
    messages_today = MailMessage.query.join(MailAccount)\
        .filter(MailAccount.user_id == current_user.id)\
        .filter(db.func.date(MailMessage.received_at) == today)\
        .count()
    
    stats = {
        'messages_today': messages_today,
        'pending_approvals': len(pending_drafts)
    }

    return render_template(
        'mailguard/dashboard.html',
        accounts=accounts,
        rules=rules,
        pending_drafts=pending_drafts,
        recent_messages=recent_messages,
        stats=stats,
        security_overview=security_overview
    )


@mailguard_bp.route('/messages')
@login_required
def messages():
    """Просмотр входящих сообщений"""
    page = request.args.get('page', 1, type=int)

    message_query = MailMessage.query.join(MailAccount).filter(
        MailAccount.user_id == current_user.id
    ).order_by(MailMessage.received_at.desc())

    pagination = message_query.paginate(page=page, per_page=15, error_out=False)

    return render_template(
        'mailguard/messages.html',
        pagination=pagination,
        messages=pagination.items
    )


@mailguard_bp.route('/messages/<int:message_id>')
@login_required
def message_detail(message_id):
    """Подробности сообщения"""
    message = MailMessage.query.join(MailAccount).filter(
        MailAccount.user_id == current_user.id,
        MailMessage.id == message_id
    ).first_or_404()

    drafts = MailDraft.query.filter_by(message_id=message.id).order_by(
        MailDraft.created_at.desc()
    ).all()

    reports = ScanReport.query.filter_by(message_id=message.id).order_by(
        ScanReport.created_at.desc()
    ).all()

    attachments = message.get_attachments()

    return render_template(
        'mailguard/message_detail.html',
        message=message,
        attachments=attachments,
        drafts=drafts,
        reports=reports
    )

@mailguard_bp.route('/accounts')
@login_required
def accounts():
    """Управление почтовыми аккаунтами"""
    accounts = MailAccount.query.filter_by(user_id=current_user.id).all()
    return render_template('mailguard/accounts.html', accounts=accounts)

@mailguard_bp.route('/rules', methods=['GET', 'POST'])
@login_required
def rules():
    """Управление правилами"""
    accounts = MailAccount.query.filter_by(user_id=current_user.id).order_by(MailAccount.email).all()

    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        match_from = (request.form.get('match_from') or '').strip() or None
        match_domain = (request.form.get('match_domain') or '').strip() or None
        match_subject_regex = (request.form.get('match_subject_regex') or '').strip() or None
        action = request.form.get('action') or 'draft'
        requires_human = bool(request.form.get('requires_human'))
        is_enabled = bool(request.form.get('is_enabled', 'on'))

        try:
            priority = int(request.form.get('priority') or 50)
        except ValueError:
            priority = 50

        if priority < 0:
            priority = 0
        if priority > 100:
            priority = 100

        if not name:
            flash('Bitte vergeben Sie einen Namen für die Regel.', 'error')
            return redirect(url_for('mailguard.rules'))

        if not any([match_from, match_domain, match_subject_regex]):
            flash('Definieren Sie mindestens eine Bedingung (Absender, Domain oder Betreff).', 'error')
            return redirect(url_for('mailguard.rules'))

        workhours_preset = request.form.get('workhours_preset', 'always')
        workhours_json = None
        if workhours_preset == 'business':
            workhours_json = json.dumps({
                'tz': 'Europe/Berlin',
                'start': '09:00',
                'end': '18:00',
                'weekdays': [0, 1, 2, 3, 4]
            })

        rule = MailRule(
            name=name,
            match_from=match_from,
            match_domain=match_domain,
            match_subject_regex=match_subject_regex,
            action=action,
            requires_human=requires_human,
            is_enabled=is_enabled,
            priority=priority,
            workhours_json=workhours_json
        )

        db.session.add(rule)
        db.session.commit()
        flash('Neue Regel gespeichert.', 'success')
        return redirect(url_for('mailguard.rules'))

    rules = MailRule.query.order_by(MailRule.priority.desc(), MailRule.name.asc()).all()

    return render_template(
        'mailguard/rules.html',
        rules=rules,
        accounts=accounts
    )

@mailguard_bp.route('/counterparties')
@login_required
def counterparties():
    """Управление известными контрагентами"""
    counterparties = KnownCounterparty.query.filter_by(is_active=True).all()
    return render_template('mailguard/counterparties.html', counterparties=counterparties)

@mailguard_bp.route('/approve/<int:draft_id>', methods=['POST'])
@login_required
def approve_and_send(draft_id):
    """Одобрить и отправить черновик"""
    draft = MailDraft.query.get_or_404(draft_id)

    # Проверяем, что черновик принадлежит пользователю
    account = MailAccount.query.filter_by(id=draft.account_id, user_id=current_user.id).first()
    if not account:
        flash('Zugriff verweigert', 'error')
        return redirect(url_for('mailguard.dashboard'))

    try:
        # Отправляем письмо через SMTP
        from .connectors.smtp import send_email
        
        success = send_email(
            account=account,
            to_email=draft.to_email,
            subject=draft.subject,
            text_content=draft.body_text or '',
            html_content=draft.body_html,
            attachments=draft.get_attachments()
        )
        
        if success:
            draft.approved_by_user = True
            draft.sent_at = datetime.utcnow()
            
            # Обновляем статус оригинального сообщения
            if draft.message:
                draft.message.status = 'sent'
            
            db.session.commit()
            flash('Entwurf erfolgreich gesendet', 'success')
        else:
            flash('Fehler beim Senden: SMTP-Verbindung fehlgeschlagen', 'error')
            
    except Exception as e:
        current_app.logger.error(f"Error sending draft {draft_id}: {e}")
        flash(f'Fehler beim Senden des Entwurfs: {str(e)}', 'error')

    return redirect(url_for('mailguard.dashboard'))

@mailguard_bp.route('/reject/<int:draft_id>', methods=['POST'])
@login_required
def reject_draft(draft_id):
    """Отклонить черновик"""
    draft = MailDraft.query.get_or_404(draft_id)

    # Проверяем, что черновик принадлежит пользователю
    account = MailAccount.query.filter_by(id=draft.account_id, user_id=current_user.id).first()
    if not account:
        flash('Zugriff verweigert', 'error')
        return redirect(url_for('mailguard.dashboard'))

    try:
        db.session.delete(draft)
        db.session.commit()
        flash('Entwurf abgelehnt', 'info')
    except Exception as e:
        current_app.logger.error(f"Error rejecting draft {draft_id}: {e}")
        flash('Fehler beim Ablehnen des Entwurfs', 'error')

    return redirect(url_for('mailguard.dashboard'))

# API endpoints für AJAX
@mailguard_bp.route('/api/accounts', methods=['GET'])
@login_required
def api_accounts():
    """API: Получить аккаунты пользователя"""
    accounts = MailAccount.query.filter_by(user_id=current_user.id, is_active=True).all()
    return jsonify([{
        'id': acc.id,
        'provider': acc.provider,
        'email': acc.email,
        'is_active': acc.is_active
    } for acc in accounts])

@mailguard_bp.route('/api/drafts/pending', methods=['GET'])
@login_required
def api_pending_drafts():
    """API: Получить ожидающие черновики"""
    drafts = MailDraft.query.join(MailMessage).join(MailAccount)\
        .filter(MailAccount.user_id == current_user.id)\
        .filter(MailDraft.approved_by_user == False)\
        .filter(MailDraft.sent_at.is_(None))\
        .order_by(MailDraft.created_at.desc())\
        .all()

    return jsonify([{
        'id': draft.id,
        'subject': draft.subject,
        'to_email': draft.to_email,
        'suggested_by': draft.suggested_by,
        'created_at': draft.created_at.isoformat(),
        'message': {
            'from_email': draft.message.from_email,
            'subject': draft.message.subject,
            'received_at': draft.message.received_at.isoformat()
        }
    } for draft in drafts])

# Webhook endpoints для почтовых провайдеров
@mailguard_bp.route('/webhook/gmail', methods=['POST'])
def gmail_webhook():
    """Webhook для Gmail push notifications"""
    # TODO: Реализовать обработку Gmail webhook
    # Верификация подписи, извлечение historyId, постановка в очередь
    return 'OK', 200

@mailguard_bp.route('/webhook/outlook', methods=['POST'])
def outlook_webhook():
    """Webhook для Microsoft Graph"""
    # TODO: Реализовать обработку Outlook webhook
    return 'OK', 200

@mailguard_bp.route('/accounts/add-imap', methods=['GET', 'POST'])
@login_required
def add_imap_account():
    """Добавить IMAP аккаунт вручную с поддержкой presets"""
    if request.method == 'GET':
        from flask_wtf import FlaskForm
        from wtforms import StringField, PasswordField, IntegerField, BooleanField, SelectField
        from wtforms.validators import DataRequired, Email
        from .presets import get_all_presets
        
        # Создаем форму с выбором провайдера
        class IMAPForm(FlaskForm):
            provider = SelectField('Провайдер', choices=[('', 'Выберите провайдер...')] + 
                                 [(p['key'], p['name']) for p in get_all_presets()])
            email = StringField('Email', validators=[DataRequired(), Email()])
            password = PasswordField('Password', validators=[DataRequired()])
            imap_host = StringField('IMAP Host', validators=[DataRequired()])
            imap_port = IntegerField('IMAP Port', default=993, validators=[DataRequired()])
            imap_ssl = BooleanField('Use SSL/TLS', default=True)
            smtp_host = StringField('SMTP Host', validators=[DataRequired()])
            smtp_port = IntegerField('SMTP Port', default=465, validators=[DataRequired()])
            smtp_ssl = BooleanField('Use SSL/TLS', default=True)
        
        form = IMAPForm()
        
        # Передаем presets в шаблон
        from .presets import EMAIL_PRESETS
        return render_template('mailguard/add_imap_improved.html', form=form, presets=EMAIL_PRESETS)
    
    # POST - сохраняем аккаунт
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        imap_host = request.form.get('imap_host')
        imap_port = int(request.form.get('imap_port', 993))
        smtp_host = request.form.get('smtp_host')
        smtp_port = int(request.form.get('smtp_port', 465))

        # Валидация
        if not email or not password or not imap_host or not smtp_host:
            flash('Bitte füllen Sie alle Pflichtfelder aus', 'error')
            return redirect(url_for('mailguard.add_imap_account'))

        # Проверяем, не существует ли уже такой аккаунт
        existing = MailAccount.query.filter_by(
            user_id=current_user.id,
            provider='imap',
            email=email
        ).first()

        if existing:
            flash(f'IMAP-Konto {email} ist bereits verbunden', 'warning')
            return redirect(url_for('mailguard.accounts'))

        # Создаем аккаунт
        from .oauth import encrypt_token
        import json
        
        # SMTP-Einstellungen werden in settings_json gespeichert
        settings = {
            'smtp_host': smtp_host,
            'smtp_port': smtp_port,
            'smtp_ssl': True
        }
        
        account = MailAccount(
            user_id=current_user.id,
            provider='imap',
            email=email,
            host=imap_host,
            port=imap_port,
            login=email,
            password=encrypt_token(password),
            settings_json=json.dumps(settings),
            is_active=True
        )
        db.session.add(account)
        db.session.commit()

        flash(f'IMAP-Konto {email} erfolgreich verbunden! Die Synchronisierung startet automatisch.', 'success')

    except Exception as e:
        current_app.logger.error(f"IMAP add error: {e}")
        flash(f'Fehler beim Hinzufügen des IMAP-Kontos: {str(e)}', 'error')

    return redirect(url_for('mailguard.accounts'))

@mailguard_bp.route('/accounts/<int:account_id>/sync', methods=['POST', 'GET'])
@login_required
def sync_account(account_id):
    """Синхронизировать аккаунт вручную"""
    account = MailAccount.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    
    try:
        processed = 0

        if account.provider == 'imap':
            processed = sync_imap_account(account)
        else:
            flash('Anbieter unterstützt keine manuelle Synchronisierung', 'warning')
            return redirect(url_for('mailguard.accounts'))

        flash(
            f'Synchronisierung von {account.email} abgeschlossen. Neue Nachrichten: {processed}',
            'success'
        )
    except Exception as e:
        current_app.logger.error(f"Sync error: {e}")
        flash('Synchronisierungsfehler', 'error')
    
    return redirect(url_for('mailguard.accounts'))

@mailguard_bp.route('/accounts/<int:account_id>/toggle', methods=['POST', 'GET'])
@login_required
def toggle_account(account_id):
    """Включить/выключить аккаунт"""
    account = MailAccount.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    
    try:
        account.is_active = not account.is_active
        db.session.commit()
        status = 'aktiviert' if account.is_active else 'deaktiviert'
        flash(f'Konto {account.email} {status}', 'success')
    except Exception as e:
        current_app.logger.error(f"Toggle error: {e}")
        flash('Fehler beim Ändern des Status', 'error')
    
    return redirect(url_for('mailguard.accounts'))

@mailguard_bp.route('/accounts/<int:account_id>/delete', methods=['POST', 'GET'])
@login_required
def delete_account(account_id):
    """Удалить аккаунт"""
    account = MailAccount.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    
    try:
        email = account.email

        messages = MailMessage.query.filter_by(account_id=account.id).all()
        for message in messages:
            db.session.query(ScanReport).filter_by(message_id=message.id).delete(synchronize_session=False)
            db.session.query(MailDraft).filter_by(message_id=message.id).delete(synchronize_session=False)
            db.session.delete(message)

        db.session.query(MailDraft).filter_by(account_id=account.id).delete(synchronize_session=False)

        db.session.delete(account)
        db.session.commit()
        flash(f'Konto {email} gelöscht', 'info')
    except Exception as e:
        current_app.logger.error(f"Delete error: {e}")
        flash('Fehler beim Löschen des Kontos', 'error')
    
    return redirect(url_for('mailguard.accounts'))


@mailguard_bp.route('/accounts/<int:account_id>/instructions', methods=['POST'])
@login_required
def update_account_instructions(account_id):
    """Обновить инструкции для генерации ответов"""
    account = MailAccount.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()

    try:
        instructions = (request.form.get('instructions') or '').strip()
        account.reply_instructions = instructions or None
        db.session.commit()

        flash('Anweisungen für KI-Antworten aktualisiert', 'success')
    except Exception as e:
        current_app.logger.error(f"Instruction update error: {e}")
        db.session.rollback()
        flash('Anweisungen konnten nicht gespeichert werden', 'error')

    return redirect(url_for('mailguard.accounts'))

@mailguard_bp.route('/drafts/<int:draft_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_draft(draft_id):
    """Редактировать черновик"""
    draft = MailDraft.query.get_or_404(draft_id)
    
    # Проверяем, что черновик принадлежит пользователю
    account = MailAccount.query.filter_by(id=draft.account_id, user_id=current_user.id).first()
    if not account:
        flash('Zugriff verweigert', 'error')
        return redirect(url_for('mailguard.dashboard'))
    
    if request.method == 'POST':
        try:
            draft.subject = request.form.get('subject', draft.subject)
            draft.body_text = request.form.get('body_text', draft.body_text)
            draft.body_html = request.form.get('body_html', draft.body_html)
            db.session.commit()
            
            flash('Entwurf erfolgreich aktualisiert', 'success')
            return redirect(url_for('mailguard.message_detail', message_id=draft.message_id))
        except Exception as e:
            current_app.logger.error(f"Draft edit error: {e}")
            flash('Fehler beim Aktualisieren des Entwurfs', 'error')
            db.session.rollback()
    
    return render_template('mailguard/edit_draft.html', draft=draft)


@mailguard_bp.route('/drafts/<int:draft_id>/regenerate', methods=['POST'])
@login_required
def regenerate_draft(draft_id):
    """Перегенерировать черновик с новыми параметрами"""
    draft = MailDraft.query.get_or_404(draft_id)
    
    # Проверяем, что черновик принадлежит пользователю
    account = MailAccount.query.filter_by(id=draft.account_id, user_id=current_user.id).first()
    if not account:
        return jsonify({'error': 'Zugriff verweigert'}), 403
    
    try:
        message = draft.message
        if not message:
            return jsonify({'error': 'Original message not found'}), 404
        
        # Получаем дополнительные инструкции от пользователя
        custom_instructions = request.form.get('instructions', '').strip()
        
        # Создаем новый черновик
        from .tasks import create_reply_draft, normalize_message
        
        # Формируем данные сообщения
        message_data = {
            'subject': message.subject,
            'text': message.body_text,
            'html': message.body_html,
            'from_email': message.from_email,
            'security': message.get_security_meta(),
            'attachments': message.get_attachments()
        }
        
        # Создаем временный профиль ассистента с кастомными инструкциями
        counterparty = message.counterparty
        
        # Удаляем старый черновик
        db.session.delete(draft)
        db.session.flush()
        
        # Создаем новый черновик
        new_draft = create_reply_draft(message, counterparty, message_data, None, account)
        
        # Если были кастомные инструкции, добавляем их в комментарий
        if custom_instructions:
            new_draft.body_text = f"[Специальные инструкции: {custom_instructions}]\n\n{new_draft.body_text}"
        
        db.session.commit()
        
        flash('Entwurf erfolgreich neu generiert', 'success')
        return redirect(url_for('mailguard.message_detail', message_id=message.id))
        
    except Exception as e:
        current_app.logger.error(f"Draft regeneration error: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@mailguard_bp.route('/messages/<int:message_id>/label', methods=['POST'])
@login_required
def label_message(message_id):
    """Добавить метку к сообщению"""
    message = MailMessage.query.join(MailAccount).filter(
        MailAccount.user_id == current_user.id,
        MailMessage.id == message_id
    ).first_or_404()
    
    try:
        label = request.form.get('label', '').strip()
        if not label:
            return jsonify({'error': 'Label is required'}), 400
        
        # Получаем текущие метки
        current_labels = message.labels.split(',') if message.labels else []
        
        # Добавляем новую метку если её нет
        if label not in current_labels:
            current_labels.append(label)
            message.labels = ','.join(current_labels)
            db.session.commit()
        
        return jsonify({'success': True, 'labels': current_labels})
    except Exception as e:
        current_app.logger.error(f"Label error: {e}")
        return jsonify({'error': str(e)}), 500


@mailguard_bp.route('/messages/<int:message_id>/unlabel', methods=['POST'])
@login_required
def unlabel_message(message_id):
    """Удалить метку из сообщения"""
    message = MailMessage.query.join(MailAccount).filter(
        MailAccount.user_id == current_user.id,
        MailMessage.id == message_id
    ).first_or_404()
    
    try:
        label = request.form.get('label', '').strip()
        if not label:
            return jsonify({'error': 'Label is required'}), 400
        
        # Получаем текущие метки
        current_labels = message.labels.split(',') if message.labels else []
        
        # Удаляем метку
        if label in current_labels:
            current_labels.remove(label)
            message.labels = ','.join(current_labels) if current_labels else None
            db.session.commit()
        
        return jsonify({'success': True, 'labels': current_labels})
    except Exception as e:
        current_app.logger.error(f"Unlabel error: {e}")
        return jsonify({'error': str(e)}), 500


@mailguard_bp.route('/messages/bulk-action', methods=['POST'])
@login_required
def bulk_action():
    """Массовые операции с сообщениями"""
    try:
        message_ids = request.form.getlist('message_ids[]')
        action = request.form.get('action')
        
        if not message_ids or not action:
            return jsonify({'error': 'Message IDs and action are required'}), 400
        
        # Получаем сообщения пользователя
        messages = MailMessage.query.join(MailAccount).filter(
            MailAccount.user_id == current_user.id,
            MailMessage.id.in_(message_ids)
        ).all()
        
        if action == 'add_label':
            label = request.form.get('label', '').strip()
            if not label:
                return jsonify({'error': 'Label is required'}), 400
            
            for message in messages:
                current_labels = message.labels.split(',') if message.labels else []
                if label not in current_labels:
                    current_labels.append(label)
                    message.labels = ','.join(current_labels)
        
        elif action == 'quarantine':
            for message in messages:
                message.status = 'quarantined'
                message.is_quarantined = True
        
        elif action == 'mark_safe':
            for message in messages:
                if message.status == 'quarantined':
                    message.status = 'scanned'
                message.is_quarantined = False
        
        else:
            return jsonify({'error': 'Unknown action'}), 400
        
        db.session.commit()
        return jsonify({'success': True, 'processed': len(messages)})
        
    except Exception as e:
        current_app.logger.error(f"Bulk action error: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
