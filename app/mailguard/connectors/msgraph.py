import requests
from flask import current_app
import json
from datetime import datetime

from ..oauth import decrypt_token

class MSGraphAPI:
    """Microsoft Graph API клиент"""

    def __init__(self, account):
        self.account = account
        self.base_url = 'https://graph.microsoft.com/v1.0'
        self.access_token = decrypt_token(account.access_token) if account.access_token else None

    def _get_headers(self):
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def _refresh_token_if_needed(self):
        """Обновить токен если истёк"""
        # TODO: Реализовать проверку и обновление токена
        pass

    def get_messages(self, folder='inbox', top=10):
        """Получить сообщения из папки"""
        try:
            url = f'{self.base_url}/me/mailFolders/{folder}/messages'
            params = {
                '$top': top,
                '$orderby': 'receivedDateTime desc',
                '$select': 'id,subject,receivedDateTime,sender,bodyPreview,hasAttachments'
            }

            response = requests.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()

            messages = []
            for msg_data in response.json().get('value', []):
                message = self._parse_message(msg_data)
                if message:
                    messages.append(message)

            return messages

        except Exception as e:
            current_app.logger.error(f"MS Graph get messages error: {e}")
            return []

    def get_message_details(self, message_id):
        """Получить детали сообщения"""
        try:
            url = f'{self.base_url}/me/messages/{message_id}'
            params = {
                '$expand': 'attachments'
            }

            response = requests.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()

            msg_data = response.json()
            return self._parse_message(msg_data, full=True)

        except Exception as e:
            current_app.logger.error(f"MS Graph get message details error: {e}")
            return None

    def _parse_message(self, msg_data, full=False):
        """Распарсить данные сообщения"""
        try:
            sender = msg_data.get('sender', {}).get('emailAddress', {})
            from_email = sender.get('address', '')

            # Парсим дату
            received_str = msg_data.get('receivedDateTime', '')
            try:
                received_at = datetime.fromisoformat(received_str.replace('Z', '+00:00'))
            except:
                received_at = datetime.utcnow()

            message = {
                'id': msg_data['id'],
                'thread_id': msg_data.get('conversationId'),
                'from_email': from_email,
                'subject': msg_data.get('subject', ''),
                'received_at': received_at,
                'meta': {
                    'is_read': msg_data.get('isRead', False),
                    'importance': msg_data.get('importance', 'normal'),
                    'has_attachments': msg_data.get('hasAttachments', False)
                }
            }

            if full:
                # Полное содержимое
                body = msg_data.get('body', {})
                if body.get('contentType') == 'html':
                    message['html'] = body.get('content', '')
                    message['text'] = self._html_to_text(message['html'])
                else:
                    message['text'] = body.get('content', '')
                    message['html'] = message['text']

                # Вложения
                message['attachments'] = self._parse_attachments(msg_data.get('attachments', []))
            else:
                # Превью
                message['text'] = msg_data.get('bodyPreview', '')
                message['html'] = message['text']

            return message

        except Exception as e:
            current_app.logger.error(f"Error parsing MS Graph message: {e}")
            return None

    def _html_to_text(self, html):
        """Простое конвертирование HTML в текст"""
        # Удаляем теги
        import re
        text = re.sub(r'<[^>]+>', '', html)
        return text.strip()

    def _parse_attachments(self, attachments_data):
        """Распарсить вложения"""
        attachments = []

        for att_data in attachments_data:
            if att_data.get('@odata.type') == '#microsoft.graph.fileAttachment':
                try:
                    attachments.append({
                        'filename': att_data.get('name', 'unknown'),
                        'content_type': att_data.get('contentType', 'application/octet-stream'),
                        'data': att_data.get('contentBytes', '')  # base64
                    })
                except Exception as e:
                    current_app.logger.error(f"Error parsing attachment: {e}")

        return attachments

    def create_draft(self, to_email, subject, body_text, body_html=None):
        """Создать черновик"""
        try:
            url = f'{self.base_url}/me/messages'

            message_data = {
                'subject': subject,
                'body': {
                    'contentType': 'html' if body_html else 'text',
                    'content': body_html or body_text
                },
                'toRecipients': [{
                    'emailAddress': {'address': to_email}
                }]
            }

            response = requests.post(url, headers=self._get_headers(), json=message_data)
            response.raise_for_status()

            draft_data = response.json()
            return draft_data['id']

        except Exception as e:
            current_app.logger.error(f"MS Graph create draft error: {e}")
            return None

    def send_draft(self, draft_id):
        """Отправить черновик"""
        try:
            url = f'{self.base_url}/me/messages/{draft_id}/send'

            response = requests.post(url, headers=self._get_headers())
            response.raise_for_status()

            return True

        except Exception as e:
            current_app.logger.error(f"MS Graph send draft error: {e}")
            return False

    def setup_webhook(self, notification_url):
        """Настроить webhook для уведомлений"""
        try:
            url = f'{self.base_url}/subscriptions'

            subscription_data = {
                'changeType': 'created',
                'notificationUrl': notification_url,
                'resource': 'me/mailFolders/inbox/messages',
                'expirationDateTime': (datetime.utcnow() + timedelta(days=3)).isoformat() + 'Z',
                'clientState': current_app.config.get('MS_WEBHOOK_SECRET', 'random_secret')
            }

            response = requests.post(url, headers=self._get_headers(), json=subscription_data)
            response.raise_for_status()

            return response.json()['id']

        except Exception as e:
            current_app.logger.error(f"MS Graph setup webhook error: {e}")
            return None

def process_ms_webhook(payload):
    """Обработать webhook от Microsoft Graph"""
    # TODO: Верификация подписи и обработка уведомлений
    # Извлечь message IDs и запустить обработку
    pass