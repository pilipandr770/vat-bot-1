import requests
import json
import base64
import tempfile
import os
from flask import current_app
from werkzeug.utils import secure_filename

def scan_message(message_data):
    """
    Отсканировать сообщение через file scanner
    message_data: dict с ключами 'text', 'attachments' и т.д.
    Возвращает: dict с verdict, score, details
    """
    scanner_url = current_app.config.get('FILE_SCANNER_URL', 'http://localhost:5001/scan')

    try:
        # Подготавливаем данные для сканирования
        scan_payload = {
            'source': 'mailguard',
            'content': {
                'text': message_data.get('text', ''),
                'html': message_data.get('html', ''),
                'subject': message_data.get('subject', ''),
                'links': extract_links(message_data)
            },
            'attachments': []
        }

        # Обрабатываем вложения
        attachments = message_data.get('attachments', [])
        for attachment in attachments:
            attachment_data = prepare_attachment_for_scan(attachment)
            if attachment_data:
                scan_payload['attachments'].append(attachment_data)

        # Отправляем на сканирование
        headers = {'Content-Type': 'application/json'}
        response = requests.post(scanner_url, json=scan_payload, headers=headers, timeout=30)

        if response.status_code == 200:
            result = response.json()
            return {
                'verdict': result.get('verdict', 'unknown'),
                'score': result.get('score', 0),
                'details': result.get('details', {}),
                'success': True
            }
        else:
            current_app.logger.error(f"Scanner error: {response.status_code} - {response.text}")
            return {
                'verdict': 'error',
                'score': 50,
                'details': {'error': f'Scanner returned {response.status_code}'},
                'success': False
            }

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Scanner connection error: {e}")
        return {
            'verdict': 'error',
            'score': 50,
            'details': {'error': f'Connection failed: {str(e)}'},
            'success': False
        }
    except Exception as e:
        current_app.logger.error(f"Scanner unexpected error: {e}")
        return {
            'verdict': 'error',
            'score': 50,
            'details': {'error': f'Unexpected error: {str(e)}'},
            'success': False
        }

def extract_links(message_data):
    """Извлечь ссылки из текста сообщения"""
    import re

    text = message_data.get('text', '') + ' ' + message_data.get('html', '')
    url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
    urls = re.findall(url_pattern, text, re.IGNORECASE)

    # Нормализуем URLs
    normalized_urls = []
    for url in urls:
        if url.startswith('www.'):
            url = 'http://' + url
        normalized_urls.append(url)

    return normalized_urls

def prepare_attachment_for_scan(attachment):
    """Подготовить вложение для сканирования"""
    try:
        # attachment должен содержать 'filename', 'content_type', 'data' (base64)
        filename = secure_filename(attachment.get('filename', 'unknown'))
        content_type = attachment.get('content_type', '')
        data_b64 = attachment.get('data', '')

        if not data_b64:
            return None

        # Декодируем base64
        file_data = base64.b64decode(data_b64)

        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
            temp_file.write(file_data)
            temp_path = temp_file.name

        return {
            'filename': filename,
            'content_type': content_type,
            'temp_path': temp_path,
            'size': len(file_data)
        }

    except Exception as e:
        current_app.logger.error(f"Error preparing attachment {attachment.get('filename')}: {e}")
        return None

def cleanup_temp_files(attachments):
    """Очистить временные файлы вложений"""
    for attachment in attachments:
        temp_path = attachment.get('temp_path')
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                current_app.logger.warning(f"Failed to cleanup {temp_path}: {e}")

def get_risk_level(score):
    """Получить уровень риска по шкале"""
    if score >= 80:
        return 'high'
    elif score >= 50:
        return 'medium'
    else:
        return 'low'