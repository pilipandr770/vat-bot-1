import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from flask import current_app

from ..oauth import decrypt_token

def send_email(account, to_email, subject, text_content, html_content=None, attachments=None):
    """
    Универсальная отправка email через SMTP

    Args:
        account: объект MailAccount
        to_email: адрес получателя
        subject: тема письма
        text_content: текстовое содержимое
        html_content: HTML содержимое (опционально)
        attachments: список вложений (опционально)

    Returns:
        bool: успех отправки
    """
    try:
        # Определяем SMTP настройки
        smtp_config = get_smtp_config(account)

        # Создаем сообщение
        msg = create_email_message(
            account.email, to_email, subject,
            text_content, html_content, attachments
        )

        # Отправляем
        return send_via_smtp(smtp_config, msg)

    except Exception as e:
        current_app.logger.error(f"Error sending email via account {account.email}: {e}")
        return False

def get_smtp_config(account):
    """Получить SMTP конфигурацию для аккаунта"""
    if account.provider == 'gmail':
        return {
            'host': 'smtp.gmail.com',
            'port': 587,
            'username': account.email,
            'password': decrypt_token(account.access_token) if account.access_token else None,
            'use_tls': True
        }
    elif account.provider == 'outlook':
        return {
            'host': 'smtp-mail.outlook.com',
            'port': 587,
            'username': account.email,
            'password': decrypt_token(account.access_token) if account.access_token else None,
            'use_tls': True
        }
    elif account.provider == 'imap':
        # Для IMAP аккаунтов используем сохраненные настройки
        return {
            'host': account.host.replace('imap', 'smtp') if account.host else 'localhost',
            'port': 587,  # По умолчанию
            'username': account.login,
            'password': decrypt_token(account.password) if account.password else None,
            'use_tls': True
        }
    else:
        # Дефолтные настройки
        return {
            'host': current_app.config.get('SMTP_HOST', 'localhost'),
            'port': current_app.config.get('SMTP_PORT', 587),
            'username': current_app.config.get('SMTP_USERNAME'),
            'password': current_app.config.get('SMTP_PASSWORD'),
            'use_tls': current_app.config.get('SMTP_USE_TLS', True)
        }

def create_email_message(from_email, to_email, subject, text_content, html_content=None, attachments=None):
    """Создать email сообщение"""
    if html_content or attachments:
        msg = MIMEMultipart('alternative')
    else:
        msg = MIMEText(text_content, 'plain', 'utf-8')

    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    # Добавляем текстовую версию
    if html_content or attachments:
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))

    # Добавляем HTML версию
    if html_content:
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    # Добавляем вложения
    if attachments:
        for attachment in attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment['data'])
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{attachment["filename"]}"'
            )
            msg.attach(part)

    return msg

def send_via_smtp(smtp_config, msg):
    """Отправить сообщение через SMTP"""
    try:
        host = smtp_config['host']
        port = smtp_config['port']
        username = smtp_config['username']
        password = smtp_config['password']
        use_tls = smtp_config['use_tls']

        if port == 465:
            # SSL
            server = smtplib.SMTP_SSL(host, port)
        else:
            # TLS или plain
            server = smtplib.SMTP(host, port)
            if use_tls:
                server.starttls()

        # Аутентификация
        if username and password:
            server.login(username, password)

        # Отправка
        server.send_message(msg)
        server.quit()

        return True

    except Exception as e:
        current_app.logger.error(f"SMTP send error: {e}")
        return False

def test_smtp_connection(account):
    """Тестировать SMTP соединение"""
    try:
        smtp_config = get_smtp_config(account)

        if smtp_config['port'] == 465:
            server = smtplib.SMTP_SSL(smtp_config['host'], smtp_config['port'])
        else:
            server = smtplib.SMTP(smtp_config['host'], smtp_config['port'])
            if smtp_config.get('use_tls'):
                server.starttls()

        if smtp_config.get('username') and smtp_config.get('password'):
            server.login(smtp_config['username'], smtp_config['password'])

        server.quit()
        return True, "SMTP connection successful"

    except Exception as e:
        return False, str(e)