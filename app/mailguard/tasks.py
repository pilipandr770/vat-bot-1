from flask import current_app
from datetime import datetime, timedelta

from .models import db

# Для простоты используем APScheduler вместо RQ/Redis
# В продакшене лучше использовать RQ + Redis или Celery

def process_incoming_email(account_id, message_data):
    """
    Обработать входящее сообщение
    Эта функция вызывается из webhook или polling
    """
    from .models import MailAccount, MailMessage, KnownCounterparty, ScanReport
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
        provider_msg_id = normalized_msg.get('provider_msg_id')

        if not provider_msg_id:
            current_app.logger.warning("Skipping message without provider_msg_id")
            return

        # Проверяем, не обрабатывали ли уже это сообщение
        existing = MailMessage.query.filter_by(
            provider_msg_id=provider_msg_id
        ).first()
        if existing:
            current_app.logger.info(f"Message {provider_msg_id} already processed")
            return

        # Определяем контрагента
        counterparty = find_or_create_counterparty(normalized_msg.get('from_email'))

        # Подготавливаем вложения
        attachments_with_data = normalized_msg.get('attachments', []) or []
        sanitized_attachments = sanitize_attachments_for_storage(attachments_with_data)

        # Создаем запись сообщения
        message = MailMessage(
            provider_msg_id=provider_msg_id,
            thread_id=normalized_msg.get('thread_id'),
            account_id=account.id,
            counterparty_id=counterparty.id if counterparty else None,
            from_email=normalized_msg.get('from_email', ''),
            subject=normalized_msg.get('subject', ''),
            body_text=normalized_msg.get('text'),
            body_html=normalized_msg.get('html'),
            received_at=normalized_msg['received_at'],
            status='new'
        )
        message.set_meta(normalized_msg.get('meta', {}))
        message.set_attachments(sanitized_attachments)

        db.session.add(message)
        db.session.flush()

        # Проверяем результаты сканирования вложений
        if message.has_dangerous_attachments or message.is_quarantined:
            message.status = 'quarantined'
            message.risk_score = 100

            report = ScanReport(
                message_id=message.id,
                verdict='malicious',
                score=100
            )
            report.set_details({
                'source': 'attachment_scanner',
                'reason': message.quarantine_reason,
                'attachments': sanitized_attachments
            })
            db.session.add(report)
            db.session.commit()

            current_app.logger.warning(
                f"Message {provider_msg_id} quarantined due to dangerous attachments"
            )
            return

        # Сканируем на угрозы (контент и ссылки)
        scan_result = scan_message(normalized_msg)
        verdict = scan_result.get('verdict', 'error')
        score = scan_result.get('score', 0)

        # Усиливаем балл риска если вложения помечены как warning
        if any(att.get('risk_level') == 'warning' for att in sanitized_attachments):
            score = max(score, 60)

        message.risk_score = score
        message.status = 'scanned'

        report_verdict = verdict if verdict in ['safe', 'suspicious', 'malicious'] else 'suspicious'
        report = ScanReport(
            message_id=message.id,
            verdict=report_verdict,
            score=score
        )
        report_details = scan_result.get('details') or {}
        report_details['attachments'] = sanitized_attachments
        report.set_details(report_details)
        db.session.add(report)

        if verdict == 'malicious':
            message.status = 'quarantined'
            db.session.commit()
            current_app.logger.warning(
                f"Message {provider_msg_id} quarantined after content scan"
            )
            return

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
                current_app.logger.info(f"Auto-reply queued for message {message.id}")
            else:
                message.status = 'drafted'

        db.session.commit()

    except Exception as e:
        current_app.logger.error(f"Error processing incoming email: {e}", exc_info=True)
        db.session.rollback()

def normalize_message(raw_message):
    """Нормализовать данные сообщения"""
    received_at = raw_message.get('received_at')

    if isinstance(received_at, str):
        try:
            received_at = datetime.fromisoformat(received_at.replace('Z', '+00:00'))
        except ValueError:
            received_at = datetime.utcnow()
    elif not isinstance(received_at, datetime):
        received_at = datetime.utcnow()

    from_email = raw_message.get('from', {}).get('email')
    if not from_email:
        from_email = raw_message.get('from_email', '')

    meta = raw_message.get('meta', {}) or {}
    history_id = raw_message.get('history_id')
    if history_id and 'history_id' not in meta:
        meta['history_id'] = history_id

    return {
        'provider_msg_id': raw_message.get('id', raw_message.get('message_id')),
        'thread_id': raw_message.get('thread_id'),
        'from_email': from_email,
        'subject': raw_message.get('subject', ''),
        'text': raw_message.get('text', ''),
        'html': raw_message.get('html', ''),
        'received_at': received_at,
        'attachments': raw_message.get('attachments', []),
        'meta': meta,
        'history_id': history_id
    }

def find_or_create_counterparty(email):
    """Найти или создать контрагента"""
    from .models import KnownCounterparty

    if not email:
        return None

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

def sanitize_attachments_for_storage(attachments):
    """Удалить бинарные данные из вложений перед сохранением в БД"""
    sanitized = []
    for attachment in attachments:
        if not isinstance(attachment, dict):
            continue
        sanitized.append({k: v for k, v in attachment.items() if k != 'data'})
    return sanitized

def sync_imap_account(account):
    """Синхронизировать отдельный IMAP аккаунт"""
    from .connectors.imap import fetch_new_imap

    try:
        current_app.logger.info(f"Polling IMAP for account {account.email}")
        new_messages = fetch_new_imap(account)

        processed = 0
        for msg_data in new_messages:
            process_incoming_email(account.id, msg_data)
            processed += 1

        account.last_sync_at = datetime.utcnow()
        db.session.commit()
        return processed

    except Exception as e:
        current_app.logger.error(f"Error polling IMAP for {account.email}: {e}")
        db.session.rollback()
        return 0

def sync_gmail_account(account):
    """Синхронизировать отдельный Gmail аккаунт"""
    from .connectors.gmail import list_new_messages

    history_id = account.last_history_id
    current_app.logger.info(
        f"Polling Gmail for {account.email} (history_id={history_id})"
    )

    try:
        new_messages = list_new_messages(account, history_id=history_id)

        latest_history = history_id
        processed = 0
        for msg_data in new_messages:
            process_incoming_email(account.id, msg_data)
            processed += 1
            msg_history_id = (
                msg_data.get('history_id')
                or (msg_data.get('meta') or {}).get('history_id')
            )
            if msg_history_id:
                latest_history = msg_history_id

        if latest_history:
            account.last_history_id = str(latest_history)

        account.last_sync_at = datetime.utcnow()
        db.session.commit()
        return processed

    except Exception as e:
        current_app.logger.error(
            f"Error polling Gmail for {account.email}: {e}",
            exc_info=True
        )
        db.session.rollback()
        return 0

def poll_imap_accounts():
    """Опрос IMAP аккаунтов на новые сообщения"""
    from .models import MailAccount

    accounts = MailAccount.query.filter_by(provider='imap', is_active=True).all()

    for account in accounts:
        sync_imap_account(account)

def poll_gmail_accounts():
    """Опрос Gmail аккаунтов на новые сообщения"""
    from .models import MailAccount

    accounts = MailAccount.query.filter_by(provider='gmail', is_active=True).all()

    for account in accounts:
        sync_gmail_account(account)

def check_expired_tokens():
    """Проверить и обновить истёкшие токены"""
    from .models import MailAccount
    from .oauth import refresh_gmail_token, refresh_ms_token, decrypt_token, encrypt_token

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

    def job_wrapper(func):
        def wrapped():
            with app.app_context():
                func()
        return wrapped

    # Опрос Gmail чаще, чтобы черновики появлялись почти сразу
    scheduler.add_job(
        func=job_wrapper(poll_gmail_accounts),
        trigger="interval",
        minutes=2,
        id='poll_gmail'
    )

    # Опрос IMAP каждые 5 минут
    scheduler.add_job(
        func=job_wrapper(poll_imap_accounts),
        trigger="interval",
        minutes=5,
        id='poll_imap'
    )

    # Проверка токенов каждый час
    scheduler.add_job(
        func=job_wrapper(check_expired_tokens),
        trigger="interval",
        hours=1,
        id='check_tokens'
    )

    scheduler.start()
    return scheduler