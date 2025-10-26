from flask import current_app
import time
from datetime import datetime
import json

# Для простоты используем APScheduler вместо RQ/Redis
# В продакшене лучше использовать RQ + Redis или Celery

def process_incoming_email(account_id, message_data):
    """
    Обработать входящее сообщение
    Эта функция вызывается из webhook или polling
    """
    from .models import db, MailAccount, MailMessage, KnownCounterparty
    from .rules import apply_rules
    from .scanner_client import scan_message
    from .nlp_reply import build_reply, get_counterparty_profile

    try:
        current_app.logger.info(f"Processing incoming email for account {account_id}")

        # Получаем аккаунт
        account = MailAccount.query.get(account_id)
        if not account:
            current_app.logger.error(f"Account {account_id} not found")
            return

        # Нормализуем данные сообщения
        normalized_msg = normalize_message(message_data)

        # Проверяем, не обрабатывали ли уже это сообщение
        existing = MailMessage.query.filter_by(
            provider_msg_id=normalized_msg['provider_msg_id']
        ).first()
        if existing:
            current_app.logger.info(f"Message {normalized_msg['provider_msg_id']} already processed")
            return

        # Определяем контрагента
        counterparty = find_or_create_counterparty(normalized_msg['from_email'])

        # Создаем запись сообщения
        message = MailMessage(
            provider_msg_id=normalized_msg['provider_msg_id'],
            thread_id=normalized_msg.get('thread_id'),
            account_id=account.id,
            counterparty_id=counterparty.id if counterparty else None,
            from_email=normalized_msg['from_email'],
            subject=normalized_msg['subject'],
            received_at=normalized_msg['received_at'],
            status='new'
        )
        message.set_meta(normalized_msg.get('meta', {}))
        db.session.add(message)
        db.session.commit()

        # Сканируем на угрозы
        scan_result = scan_message(normalized_msg)
        message.risk_score = scan_result['score']
        message.status = 'scanned'

        # Сохраняем отчёт сканирования
        from .models import ScanReport
        report = ScanReport(
            message_id=message.id,
            verdict=scan_result['verdict'],
            score=scan_result['score']
        )
        report.set_details(scan_result['details'])
        db.session.add(report)
        db.session.commit()

        # Применяем правила
        action, requires_human, matched_rule = apply_rules(normalized_msg)

        if action == 'ignore':
            message.status = 'skipped'
            db.session.commit()
            return

        if action == 'quarantine':
            message.status = 'quarantined'
            db.session.commit()
            return

        # Создаем черновик ответа
        if action in ['auto_reply', 'draft']:
            draft = create_reply_draft(message, counterparty, normalized_msg, matched_rule)

            if action == 'auto_reply' and not requires_human:
                # Автоматическая отправка
                draft.approved_by_user = True
                draft.sent_at = datetime.utcnow()
                message.status = 'sent'
                # TODO: Реализовать отправку
                current_app.logger.info(f"Auto-reply sent for message {message.id}")
            else:
                message.status = 'drafted'

            db.session.commit()

    except Exception as e:
        current_app.logger.error(f"Error processing incoming email: {e}")
        db.session.rollback()

def normalize_message(raw_message):
    """Нормализовать данные сообщения"""
    return {
        'provider_msg_id': raw_message.get('id', raw_message.get('message_id')),
        'thread_id': raw_message.get('thread_id'),
        'from_email': raw_message.get('from', {}).get('email', raw_message.get('from_email', '')),
        'subject': raw_message.get('subject', ''),
        'text': raw_message.get('text', ''),
        'html': raw_message.get('html', ''),
        'received_at': raw_message.get('received_at', datetime.utcnow()),
        'attachments': raw_message.get('attachments', []),
        'meta': raw_message.get('meta', {})
    }

def find_or_create_counterparty(email):
    """Найти или создать контрагента"""
    from .models import KnownCounterparty

    # Извлекаем домен
    domain = email.split('@')[-1] if '@' in email else ''

    # Ищем существующего
    counterparty = KnownCounterparty.query.filter_by(email=email).first()
    if counterparty:
        return counterparty

    # Создаем нового
    counterparty = KnownCounterparty(
        display_name=email.split('@')[0],  # Простое имя
        email=email,
        domain=domain
    )
    db.session.add(counterparty)
    db.session.commit()

    return counterparty

def create_reply_draft(message, counterparty, message_data, matched_rule):
    """Создать черновик ответа"""
    from .models import MailDraft
    from .nlp_reply import build_reply, get_counterparty_profile

    # Получаем профиль контрагента
    profile = get_counterparty_profile(counterparty) if counterparty else {}

    # Получаем историю переписки
    thread_history = []  # TODO: Реализовать

    # Генерируем ответ
    reply = build_reply(profile, thread_history, message_data)

    # Создаем черновик
    draft = MailDraft(
        message_id=message.id,
        account_id=message.account_id,
        to_email=message.from_email,
        subject=f"Re: {message.subject}",
        body_text=reply['text'],
        body_html=reply['html'],
        suggested_by='assistant'
    )

    db.session.add(draft)
    return draft

def poll_imap_accounts():
    """Опрос IMAP аккаунтов на новые сообщения"""
    from .models import MailAccount
    from .connectors.imap import fetch_new_imap

    accounts = MailAccount.query.filter_by(provider='imap', is_active=True).all()

    for account in accounts:
        try:
            current_app.logger.info(f"Polling IMAP for account {account.email}")
            new_messages = fetch_new_imap(account)

            for msg_data in new_messages:
                process_incoming_email(account.id, msg_data)

        except Exception as e:
            current_app.logger.error(f"Error polling IMAP for {account.email}: {e}")

def check_expired_tokens():
    """Проверить и обновить истёкшие токены"""
    from .models import MailAccount
    from .oauth import refresh_gmail_token, refresh_ms_token, decrypt_token, encrypt_token
    from datetime import datetime

    accounts = MailAccount.query.filter(
        MailAccount.expires_at < datetime.utcnow(),
        MailAccount.refresh_token.isnot(None)
    ).all()

    for account in accounts:
        try:
            refresh_token = decrypt_token(account.refresh_token)

            if account.provider == 'gmail':
                new_tokens = refresh_gmail_token(refresh_token)
            elif account.provider == 'outlook':
                new_tokens = refresh_ms_token(refresh_token)
            else:
                continue

            # Обновляем токены
            account.access_token = encrypt_token(new_tokens.get('access_token'))
            account.refresh_token = encrypt_token(new_tokens.get('refresh_token', refresh_token))
            account.expires_at = datetime.utcnow() + timedelta(seconds=new_tokens.get('expires_in', 3600))

            db.session.commit()
            current_app.logger.info(f"Refreshed tokens for {account.email}")

        except Exception as e:
            current_app.logger.error(f"Error refreshing tokens for {account.email}: {e}")

# Планировщик задач (простая реализация)
def setup_scheduler(app):
    """Настроить планировщик задач"""
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler()

    # Опрос IMAP каждые 5 минут
    scheduler.add_job(
        func=lambda: app.app_context().push() or poll_imap_accounts(),
        trigger="interval",
        minutes=5,
        id='poll_imap'
    )

    # Проверка токенов каждый час
    scheduler.add_job(
        func=lambda: app.app_context().push() or check_expired_tokens(),
        trigger="interval",
        hours=1,
        id='check_tokens'
    )

    scheduler.start()
    return scheduler