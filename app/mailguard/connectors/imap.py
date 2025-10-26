import imaplib
import email
import email.header
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
from datetime import datetime
import smtplib
import ssl

from ..oauth import decrypt_token

def fetch_new_imap(account):
    """Получить новые сообщения через IMAP"""
    try:
        # Подключаемся к IMAP
        if account.port == 993:
            mail = imaplib.IMAP4_SSL(account.host, account.port)
        else:
            mail = imaplib.IMAP4(account.host, account.port)
            mail.starttls()

        # Аутентификация
        password = decrypt_token(account.password) if account.password else None
        if password:
            mail.login(account.login, password)
        else:
            current_app.logger.error(f"No password for IMAP account {account.email}")
            return []

        # Выбираем INBOX
        mail.select('INBOX')

        # Ищем непрочитанные сообщения
        status, messages = mail.search(None, 'UNSEEN')
        if status != 'OK':
            current_app.logger.error(f"IMAP search failed for {account.email}")
            return []

        message_ids = messages[0].split()
        new_messages = []

        for msg_id in message_ids[-10:]:  # Обрабатываем последние 10
            try:
                # Получаем сообщение
                status, msg_data = mail.fetch(msg_id, '(RFC822)')
                if status != 'OK':
                    continue

                email_message = email.message_from_bytes(msg_data[0][1])
                parsed_message = parse_email_message(email_message, msg_id.decode())

                if parsed_message:
                    new_messages.append(parsed_message)

                # Помечаем как прочитанное
                mail.store(msg_id, '+FLAGS', '\\Seen')

            except Exception as e:
                current_app.logger.error(f"Error processing IMAP message {msg_id}: {e}")

        mail.logout()
        return new_messages

    except Exception as e:
        current_app.logger.error(f"IMAP error for {account.email}: {e}")
        return []

def parse_email_message(email_message, message_id):
    """Распарсить email сообщение"""
    try:
        # Извлекаем заголовки
        subject = decode_header(email_message.get('Subject', ''))
        from_email = decode_header(email_message.get('From', ''))
        to_email = decode_header(email_message.get('To', ''))
        date_str = email_message.get('Date', '')

        # Парсим дату
        try:
            received_at = email.utils.parsedate_to_datetime(date_str)
        except:
            received_at = datetime.utcnow()

        # Извлекаем содержимое
        text_content, html_content = extract_email_content(email_message)

        # Извлекаем вложения
        attachments = extract_email_attachments(email_message)

        # Thread ID (Message-ID для простоты)
        thread_id = email_message.get('Message-ID', message_id)

        return {
            'id': message_id,
            'thread_id': thread_id,
            'from_email': extract_email_address(from_email),
            'to_email': extract_email_address(to_email),
            'subject': subject,
            'text': text_content,
            'html': html_content,
            'received_at': received_at,
            'attachments': attachments,
            'meta': {
                'message_id': email_message.get('Message-ID', ''),
                'in_reply_to': email_message.get('In-Reply-To', ''),
                'references': email_message.get('References', '')
            }
        }

    except Exception as e:
        current_app.logger.error(f"Error parsing email message: {e}")
        return None

def decode_header(header_value):
    """Декодировать заголовок email"""
    if not header_value:
        return ''

    try:
        decoded_parts = email.header.decode_header(header_value)
        decoded_string = ''
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_string += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                decoded_string += str(part)
        return decoded_string
    except:
        return str(header_value)

def extract_email_address(header_value):
    """Извлечь email адрес из заголовка From/To"""
    try:
        # Простой парсинг
        import re
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', header_value)
        return email_match.group(0) if email_match else header_value
    except:
        return header_value

def extract_email_content(email_message):
    """Извлечь текстовое содержимое email"""
    text_content = ""
    html_content = ""

    if email_message.is_multipart():
        for part in email_message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition'))

            # Пропускаем вложения
            if 'attachment' in content_disposition:
                continue

            try:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    content = payload.decode(charset, errors='ignore')

                    if content_type == 'text/plain':
                        text_content += content
                    elif content_type == 'text/html':
                        html_content += content
            except Exception as e:
                current_app.logger.debug(f"Error extracting part content: {e}")
    else:
        # Простое сообщение
        try:
            payload = email_message.get_payload(decode=True)
            if payload:
                charset = email_message.get_content_charset() or 'utf-8'
                content = payload.decode(charset, errors='ignore')
                text_content = content
                html_content = content
        except Exception as e:
            current_app.logger.debug(f"Error extracting message content: {e}")

    return text_content.strip(), html_content.strip()

def extract_email_attachments(email_message):
    """Извлечь вложения из email"""
    attachments = []

    for part in email_message.walk():
        content_disposition = str(part.get('Content-Disposition'))

        if 'attachment' in content_disposition:
            filename = part.get_filename()
            if filename:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        # Кодируем в base64 для передачи
                        encoded_data = base64.b64encode(payload).decode('utf-8')

                        attachments.append({
                            'filename': decode_header(filename),
                            'content_type': part.get_content_type(),
                            'data': encoded_data
                        })
                except Exception as e:
                    current_app.logger.error(f"Error extracting attachment {filename}: {e}")

    return attachments

def send_via_smtp(account, to_email, subject, text_content, html_content=None, attachments=None):
    """Отправить сообщение через SMTP"""
    try:
        # Создаем сообщение
        if html_content or attachments:
            msg = MIMEMultipart('alternative')
            if html_content:
                msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        else:
            msg = MIMEText(text_content, 'plain', 'utf-8')

        msg['Subject'] = subject
        msg['From'] = account.email
        msg['To'] = to_email

        # TODO: Добавить вложения если нужны

        # Подключаемся к SMTP
        smtp_host = account.host.replace('imap', 'smtp')  # Простая замена
        smtp_port = 587 if account.port == 143 else 465  # Простая логика

        password = decrypt_token(account.password) if account.password else None
        if not password:
            raise ValueError("No password for SMTP")

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()

        server.login(account.login, password)
        server.send_message(msg)
        server.quit()

        return True

    except Exception as e:
        current_app.logger.error(f"SMTP send error for {account.email}: {e}")
        return False