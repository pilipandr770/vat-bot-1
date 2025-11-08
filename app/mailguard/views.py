from flask import render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import json
import os
import requests
from datetime import datetime, timedelta

from . import mailguard_bp
from .models import db, MailAccount, KnownCounterparty, MailRule, MailMessage, MailDraft, ScanReport
from .tasks import sync_gmail_account, sync_imap_account
from .oauth import (
    get_gmail_auth_url, exchange_gmail_code, 
    get_ms_auth_url, exchange_ms_code,
    encrypt_token, get_gmail_email
)

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

@mailguard_bp.route('/rules')
@login_required
def rules():
    """Управление правилами"""
    rules = MailRule.query.order_by(MailRule.priority.desc()).all()
    return render_template('mailguard/rules.html', rules=rules)

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
        flash('Доступ запрещён', 'error')
        return redirect(url_for('mailguard.dashboard'))

    try:
        draft.approved_by_user = True
        draft.sent_at = datetime.utcnow()
        db.session.commit()

        # TODO: Реализовать отправку через соответствующий коннектор
        # send_draft(draft, account)

        flash('Черновик отправлен успешно', 'success')
    except Exception as e:
        current_app.logger.error(f"Error sending draft {draft_id}: {e}")
        flash('Ошибка при отправке черновика', 'error')

    return redirect(url_for('mailguard.dashboard'))

@mailguard_bp.route('/reject/<int:draft_id>', methods=['POST'])
@login_required
def reject_draft(draft_id):
    """Отклонить черновик"""
    draft = MailDraft.query.get_or_404(draft_id)

    # Проверяем, что черновик принадлежит пользователю
    account = MailAccount.query.filter_by(id=draft.account_id, user_id=current_user.id).first()
    if not account:
        flash('Доступ запрещён', 'error')
        return redirect(url_for('mailguard.dashboard'))

    try:
        db.session.delete(draft)
        db.session.commit()
        flash('Черновик отклонён', 'info')
    except Exception as e:
        current_app.logger.error(f"Error rejecting draft {draft_id}: {e}")
        flash('Ошибка при отклонении черновика', 'error')

    return redirect(url_for('mailguard.dashboard'))

# API endpoints для AJAX
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

# ========== OAuth Routes ==========

@mailguard_bp.route('/auth/gmail')
@login_required
def auth_gmail():
    """Инициировать OAuth для Gmail"""
    try:
        auth_url = get_gmail_auth_url()
        return redirect(auth_url)
    except Exception as e:
        current_app.logger.error(f"Gmail OAuth init error: {e}")
        flash('Ошибка при подключении Gmail. Проверьте настройки API.', 'error')
        return redirect(url_for('mailguard.accounts'))

@mailguard_bp.route('/auth/gmail/callback')
@login_required
def gmail_callback():
    """Callback после авторизации Gmail"""
    code = request.args.get('code')
    error = request.args.get('error')

    if error:
        flash(f'Ошибка авторизации Gmail: {error}', 'error')
        return redirect(url_for('mailguard.accounts'))

    if not code:
        flash('Не получен код авторизации от Google', 'error')
        return redirect(url_for('mailguard.accounts'))

    try:
        # Обмениваем код на токены
        tokens = exchange_gmail_code(code)
        
        # Получаем email пользователя
        email = get_gmail_email(tokens['access_token'])

        # Проверяем, не подключен ли уже этот аккаунт
        existing = MailAccount.query.filter_by(
            user_id=current_user.id,
            provider='gmail',
            email=email
        ).first()

        if existing:
            # Обновляем токены
            existing.access_token = encrypt_token(tokens['access_token'])
            existing.refresh_token = encrypt_token(tokens.get('refresh_token', ''))
            existing.expires_at = datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600))
            existing.is_active = True
            db.session.commit()
            synced = sync_gmail_account(existing)
            flash(f'Gmail аккаунт {email} успешно переподключен!', 'success')
            if synced:
                flash(f'Получено новых писем: {synced}', 'success')
        else:
            # Создаем новый аккаунт
            account = MailAccount(
                user_id=current_user.id,
                provider='gmail',
                email=email,
                access_token=encrypt_token(tokens['access_token']),
                refresh_token=encrypt_token(tokens.get('refresh_token', '')),
                expires_at=datetime.utcnow() + timedelta(seconds=tokens.get('expires_in', 3600)),
                is_active=True
            )
            db.session.add(account)
            db.session.commit()
            synced = sync_gmail_account(account)
            flash(f'Gmail аккаунт {email} успешно подключен!', 'success')
            if synced:
                flash(f'Получено новых писем: {synced}', 'success')

    except Exception as e:
        current_app.logger.error(f"Gmail callback error: {e}")
        flash('Ошибка при сохранении токенов Gmail. Попробуйте еще раз.', 'error')

    return redirect(url_for('mailguard.accounts'))

@mailguard_bp.route('/auth/microsoft')
@login_required
def auth_microsoft():
    """Инициировать OAuth для Microsoft"""
    try:
        auth_url = get_ms_auth_url()
        return redirect(auth_url)
    except Exception as e:
        current_app.logger.error(f"Microsoft OAuth init error: {e}")
        flash('Ошибка при подключении Microsoft. Проверьте настройки API.', 'error')
        return redirect(url_for('mailguard.accounts'))

@mailguard_bp.route('/auth/microsoft/callback')
@login_required
def microsoft_callback():
    """Callback после авторизации Microsoft"""
    code = request.args.get('code')
    error = request.args.get('error')

    if error:
        flash(f'Ошибка авторизации Microsoft: {error}', 'error')
        return redirect(url_for('mailguard.accounts'))

    if not code:
        flash('Не получен код авторизации от Microsoft', 'error')
        return redirect(url_for('mailguard.accounts'))

    try:
        # Обмениваем код на токены
        result = exchange_ms_code(code)
        
        # Получаем email пользователя из Microsoft Graph
        headers = {'Authorization': f"Bearer {result['access_token']}"}
        user_info = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers).json()
        email = user_info.get('mail') or user_info.get('userPrincipalName')

        # Проверяем, не подключен ли уже этот аккаунт
        existing = MailAccount.query.filter_by(
            user_id=current_user.id,
            provider='microsoft',
            email=email
        ).first()

        if existing:
            # Обновляем токены
            existing.access_token = encrypt_token(result['access_token'])
            existing.refresh_token = encrypt_token(result.get('refresh_token', ''))
            existing.expires_at = datetime.utcnow() + timedelta(seconds=result.get('expires_in', 3600))
            existing.is_active = True
            db.session.commit()
            flash(f'Microsoft аккаунт {email} успешно переподключен!', 'success')
        else:
            # Создаем новый аккаунт
            account = MailAccount(
                user_id=current_user.id,
                provider='microsoft',
                email=email,
                access_token=encrypt_token(result['access_token']),
                refresh_token=encrypt_token(result.get('refresh_token', '')),
                expires_at=datetime.utcnow() + timedelta(seconds=result.get('expires_in', 3600)),
                is_active=True
            )
            db.session.add(account)
            db.session.commit()
            flash(f'Microsoft аккаунт {email} успешно подключен!', 'success')

    except Exception as e:
        current_app.logger.error(f"Microsoft callback error: {e}")
        flash('Ошибка при сохранении токенов Microsoft. Попробуйте еще раз.', 'error')

    return redirect(url_for('mailguard.accounts'))

@mailguard_bp.route('/accounts/add-imap', methods=['GET', 'POST'])
@login_required
def add_imap_account():
    """Добавить IMAP аккаунт вручную"""
    if request.method == 'GET':
        from flask_wtf import FlaskForm
        from wtforms import StringField, PasswordField, IntegerField, BooleanField
        from wtforms.validators import DataRequired, Email
        
        # Создаем простую форму
        class IMAPForm(FlaskForm):
            email = StringField('Email', validators=[DataRequired(), Email()])
            password = PasswordField('Password', validators=[DataRequired()])
            imap_host = StringField('IMAP Host', validators=[DataRequired()])
            imap_port = IntegerField('IMAP Port', default=993, validators=[DataRequired()])
            imap_ssl = BooleanField('Use SSL/TLS', default=True)
            smtp_host = StringField('SMTP Host', validators=[DataRequired()])
            smtp_port = IntegerField('SMTP Port', default=465, validators=[DataRequired()])
            smtp_ssl = BooleanField('Use SSL/TLS', default=True)
        
        form = IMAPForm()
        return render_template('mailguard/add_imap.html', form=form)
    
    # POST - сохраняем аккаунт
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        imap_host = request.form.get('imap_host')
        imap_port = int(request.form.get('imap_port', 993))
        smtp_host = request.form.get('smtp_host')
        smtp_port = int(request.form.get('smtp_port', 465))

        # Проверяем подключение (быстрый тест)
        from .connectors.imap import IMAPConnector
        test_connector = IMAPConnector(imap_host, imap_port, email, password, use_ssl=True)
        if not test_connector.connect():
            flash('Не удалось подключиться к IMAP серверу. Проверьте настройки.', 'error')
            return redirect(url_for('mailguard.add_imap_account'))

        # Проверяем, не существует ли уже такой аккаунт
        existing = MailAccount.query.filter_by(
            user_id=current_user.id,
            provider='imap',
            email=email
        ).first()

        if existing:
            flash(f'IMAP аккаунт {email} уже подключен', 'warning')
            return redirect(url_for('mailguard.accounts'))

        # Создаем аккаунт
        account = MailAccount(
            user_id=current_user.id,
            provider='imap',
            email=email,
            host=imap_host,
            port=imap_port,
            login=email,
            password=encrypt_token(password),
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            is_active=True
        )
        db.session.add(account)
        db.session.commit()

        flash(f'IMAP аккаунт {email} успешно подключен!', 'success')

    except Exception as e:
        current_app.logger.error(f"IMAP add error: {e}")
        flash('Ошибка при добавлении IMAP аккаунта', 'error')

    return redirect(url_for('mailguard.accounts'))

@mailguard_bp.route('/accounts/<int:account_id>/sync', methods=['POST', 'GET'])
@login_required
def sync_account(account_id):
    """Синхронизировать аккаунт вручную"""
    account = MailAccount.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    
    try:
        processed = 0

        if account.provider == 'gmail':
            processed = sync_gmail_account(account)
        elif account.provider == 'imap':
            processed = sync_imap_account(account)
        else:
            flash('Провайдер не поддерживает ручную синхронизацию', 'warning')
            return redirect(url_for('mailguard.accounts'))

        flash(
            f'Синхронизация {account.email} завершена. Новых писем: {processed}',
            'success'
        )
    except Exception as e:
        current_app.logger.error(f"Sync error: {e}")
        flash('Ошибка синхронизации', 'error')
    
    return redirect(url_for('mailguard.accounts'))

@mailguard_bp.route('/accounts/<int:account_id>/toggle', methods=['POST', 'GET'])
@login_required
def toggle_account(account_id):
    """Включить/выключить аккаунт"""
    account = MailAccount.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    
    try:
        account.is_active = not account.is_active
        db.session.commit()
        status = 'включен' if account.is_active else 'выключен'
        flash(f'Аккаунт {account.email} {status}', 'success')
    except Exception as e:
        current_app.logger.error(f"Toggle error: {e}")
        flash('Ошибка изменения статуса', 'error')
    
    return redirect(url_for('mailguard.accounts'))

@mailguard_bp.route('/accounts/<int:account_id>/delete', methods=['POST', 'GET'])
@login_required
def delete_account(account_id):
    """Удалить аккаунт"""
    account = MailAccount.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    
    try:
        email = account.email
        db.session.delete(account)
        db.session.commit()
        flash(f'Аккаунт {email} удален', 'info')
    except Exception as e:
        current_app.logger.error(f"Delete error: {e}")
        flash('Ошибка удаления аккаунта', 'error')
    
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

        flash('Инструкции для AI-ответов обновлены', 'success')
    except Exception as e:
        current_app.logger.error(f"Instruction update error: {e}")
        db.session.rollback()
        flash('Не удалось сохранить инструкции', 'error')

    return redirect(url_for('mailguard.accounts'))