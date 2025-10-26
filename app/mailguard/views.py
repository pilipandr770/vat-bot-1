from flask import render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import json
import os
from datetime import datetime

from . import mailguard_bp
from .models import db, MailAccount, KnownCounterparty, MailRule, MailMessage, MailDraft, ScanReport

@mailguard_bp.route('/')
@login_required
def dashboard():
    """Главная страница MailGuard"""
    # Получаем подключенные аккаунты
    accounts = MailAccount.query.filter_by(user_id=current_user.id, is_active=True).all()

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

    return render_template('mailguard/dashboard.html',
                         accounts=accounts,
                         pending_drafts=pending_drafts,
                         recent_messages=recent_messages)

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