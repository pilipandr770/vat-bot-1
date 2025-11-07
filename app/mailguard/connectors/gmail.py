from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from flask import current_app
import base64
import json
from email.mime.text import MIMEText
from datetime import datetime

from ..oauth import decrypt_token

def get_gmail_service(account):
    """Получить Gmail API сервис для аккаунта"""
    try:
        access_token = decrypt_token(account.access_token)

        creds = Credentials(
            token=access_token,
            refresh_token=decrypt_token(account.refresh_token),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=current_app.config.get('GMAIL_CLIENT_ID'),
            client_secret=current_app.config.get('GMAIL_CLIENT_SECRET')
        )

        # Проверяем и обновляем токен если нужно
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

            # Сохраняем обновленный токен
            from ..oauth import encrypt_token
            from ..models import db
            account.access_token = encrypt_token(creds.token)
            account.expires_at = creds.expiry
            db.session.commit()

        return build('gmail', 'v1', credentials=creds)

    except Exception as e:
        current_app.logger.error(f"Error creating Gmail service for {account.email}: {e}")
        return None

def watch_gmail(account):
    """Настроить Gmail push notifications"""
    service = get_gmail_service(account)
    if not service:
        return False

    try:
        # Настраиваем watch
        request = {
            'topicName': current_app.config.get('GMAIL_PUBSUB_TOPIC'),
            'labelIds': ['INBOX']
        }

        response = service.users().watch(userId='me', body=request).execute()
        current_app.logger.info(f"Gmail watch started for {account.email}: {response}")
        return True

    except HttpError as e:
        current_app.logger.error(f"Gmail watch error for {account.email}: {e}")
        return False

def list_new_messages(account, history_id=None):
    """Получить новые сообщения с history ID"""
    service = get_gmail_service(account)
    if not service:
        return []

    try:
        if history_id:
            # Используем history API
            history = service.users().history().list(
                userId='me',
                startHistoryId=history_id,
                labelId='INBOX'
            ).execute()

            messages = []
            for history_item in history.get('history', []):
                for message_item in history_item.get('messages', []):
                    msg = get_message_details(service, message_item['id'])
                    if msg:
                        messages.append(msg)
            return messages
        else:
            # Получаем последние сообщения
            results = service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                maxResults=10
            ).execute()

            messages = []
            for msg_item in results.get('messages', []):
                msg = get_message_details(service, msg_item['id'])
                if msg:
                    messages.append(msg)
            return messages

    except HttpError as e:
        current_app.logger.error(f"Error listing Gmail messages for {account.email}: {e}")
        return []

def get_message_details(service, message_id):
    """Получить детали сообщения"""
    try:
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()

        # Парсим заголовки
        headers = {}
        for header in message['payload']['headers']:
            headers[header['name'].lower()] = header['value']

        # Извлекаем текст
        text_content, html_content = extract_message_content(message['payload'])

        # Извлекаем вложения
        attachments = extract_attachments(service, message)

        return {
            'id': message_id,
            'thread_id': message.get('threadId'),
            'from_email': headers.get('from', ''),
            'subject': headers.get('subject', ''),
            'text': text_content,
            'html': html_content,
            'received_at': datetime.fromtimestamp(int(message['internalDate']) / 1000),
            'attachments': attachments,
            'meta': {
                'labels': message.get('labelIds', []),
                'size': message.get('sizeEstimate', 0)
            }
        }

    except Exception as e:
        current_app.logger.error(f"Error getting message {message_id}: {e}")
        return None

def extract_message_content(payload):
    """Извлечь текстовое содержимое сообщения"""
    text_content = ""
    html_content = ""

    def extract_parts(parts):
        nonlocal text_content, html_content

        for part in parts:
            mime_type = part.get('mimeType', '')

            if mime_type == 'text/plain':
                if 'data' in part['body']:
                    text_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
            elif mime_type == 'text/html':
                if 'data' in part['body']:
                    html_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
            elif 'parts' in part:
                extract_parts(part['parts'])

    if 'parts' in payload:
        extract_parts(payload['parts'])
    elif 'body' in payload and 'data' in payload['body']:
        # Простое сообщение
        content = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        text_content = content
        html_content = content

    return text_content, html_content

def extract_attachments(service, message):
    """Извлечь вложения из сообщения + СКАНИРОВАТЬ на безопасность"""
    from ..attachment_scanner import AttachmentScanner
    
    scanner = AttachmentScanner()
    attachments = []

    def extract_from_parts(parts):
        for part in parts:
            if part.get('filename') and 'attachmentId' in part.get('body', {}):
                attachment_id = part['body']['attachmentId']
                filename = part['filename']
                mime_type = part.get('mimeType', '')
                size = part.get('body', {}).get('size', 0)

                # Скачиваем вложение В ПАМЯТЬ (base64)
                try:
                    attachment = service.users().messages().attachments().get(
                        userId='me',
                        messageId=message['id'],
                        id=attachment_id
                    ).execute()

                    data_b64 = attachment['data']
                    
                    # 🛡️ СКАНИРУЕМ НА СЕРВЕРЕ (ДО того как пользователь скачает!)
                    current_app.logger.info(f"Scanning attachment: {filename}")
                    scan_result = scanner.scan_gmail_attachment(
                        attachment_data_b64=data_b64,
                        filename=filename,
                        mime_type=mime_type,
                        size=size
                    )
                    
                    current_app.logger.info(
                        f"Scan complete for {filename}: "
                        f"risk_level={scan_result['risk_level']}, "
                        f"is_safe={scan_result.get('is_safe')}"
                    )
                    
                    attachments.append({
                        'filename': filename,
                        'content_type': mime_type,
                        'size': size,
                        'data': data_b64,  # Сохраняем base64 для дальнейшей загрузки
                        'scan_result': scan_result,  # ← НОВОЕ! Результаты сканирования
                        'is_safe': scan_result.get('is_safe'),
                        'risk_level': scan_result.get('risk_level'),
                        'sha256': scan_result.get('sha256'),
                        'threats': scan_result.get('threats', [])
                    })

                except Exception as e:
                    current_app.logger.error(f"Error processing attachment {filename}: {e}", exc_info=True)
                    # Добавляем вложение с ошибкой сканирования
                    attachments.append({
                        'filename': filename,
                        'content_type': mime_type,
                        'size': size,
                        'scan_result': {'error': str(e)},
                        'is_safe': False,
                        'risk_level': 'warning',
                        'threats': ['Ошибка сканирования']
                    })

            elif 'parts' in part:
                extract_from_parts(part['parts'])

    if 'payload' in message and 'parts' in message['payload']:
        extract_from_parts(message['payload']['parts'])

    return attachments

def create_draft(service, to_email, subject, text_content, html_content=None, thread_id=None):
    """Создать черновик в Gmail"""
    try:
        message = MIMEText(text_content, 'plain', 'utf-8')
        if html_content:
            # Для HTML можно использовать email.mime.multipart
            pass

        message['to'] = to_email
        message['subject'] = subject

        if thread_id:
            message['threadId'] = thread_id

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        draft_body = {'message': {'raw': raw_message}}
        if thread_id:
            draft_body['message']['threadId'] = thread_id

        draft = service.users().drafts().create(userId='me', body=draft_body).execute()
        return draft['id']

    except Exception as e:
        current_app.logger.error(f"Error creating Gmail draft: {e}")
        return None

def send_draft(service, draft_id):
    """Отправить черновик"""
    try:
        sent_message = service.users().drafts().send(
            userId='me',
            body={'id': draft_id}
        ).execute()
        return sent_message['id']

    except Exception as e:
        current_app.logger.error(f"Error sending Gmail draft {draft_id}: {e}")
        return None