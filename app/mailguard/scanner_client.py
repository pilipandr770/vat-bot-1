import requests
import base64
import tempfile
import os
from flask import current_app
from werkzeug.utils import secure_filename


class ScannerUnavailable(RuntimeError):
    """Raised when the external file scanner cannot be used."""

def scan_message(message_data):
    """Попытаться отсканировать сообщение через внешний сервис, fallback на локальную эвристику."""
    scanner_url = current_app.config.get('FILE_SCANNER_URL')
    scanner_enabled = current_app.config.get('FILE_SCANNER_ENABLED', True)
    scanner_timeout = current_app.config.get('FILE_SCANNER_TIMEOUT', 30)

    attachments = message_data.get('attachments', []) or []
    prepared_attachments = []

    try:
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

        for attachment in attachments:
            attachment_data = prepare_attachment_for_scan(attachment)
            if attachment_data:
                prepared_attachments.append(attachment_data)
                scan_payload['attachments'].append(attachment_data)

        if not scanner_enabled or not scanner_url:
            raise ScannerUnavailable('External file scanner disabled')

        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            scanner_url,
            json=scan_payload,
            headers=headers,
            timeout=scanner_timeout
        )

        if response.status_code == 200:
            result = response.json()
            return {
                'verdict': result.get('verdict', 'unknown'),
                'score': result.get('score', 0),
                'details': result.get('details', {}),
                'success': True,
                'source': 'external'
            }

        current_app.logger.error(
            f"Scanner error ({response.status_code}): {response.text}"
        )
        raise ScannerUnavailable(f"External scanner returned HTTP {response.status_code}")

    except (requests.exceptions.RequestException, ScannerUnavailable) as e:
        current_app.logger.warning(
            f"Falling back to local message scan: {e}"
        )
        fallback_details = local_message_scan(message_data, attachments)
        fallback_details['details']['fallback_reason'] = str(e)
        return fallback_details

    except Exception as e:
        current_app.logger.error(f"Scanner unexpected error: {e}", exc_info=True)
        fallback_details = local_message_scan(message_data, attachments)
        fallback_details['details']['fallback_reason'] = f'unexpected_error: {str(e)}'
        return fallback_details

    finally:
        cleanup_temp_files(prepared_attachments)

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

def local_message_scan(message_data, attachments):
    """Простейшая локальная эвристика на случай недоступности внешнего сканера."""
    text = message_data.get('text') or ''
    html = message_data.get('html') or ''
    subject = message_data.get('subject') or ''
    combined_text = ' '.join([subject, text, html]).lower()

    suspicious_keywords = [
        'überweisen', 'zahlung dringend', 'sofort überweisung', 'bitcoin',
        'gift card', 'geschenkkarte', 'bankdaten', 'passwort zurücksetzen',
        'invoice attached', 'faktura im anhang', 'anhang öffnen'
    ]

    detected_keywords = [kw for kw in suspicious_keywords if kw in combined_text]
    links = extract_links(message_data)

    dangerous_attachments = [att for att in attachments if att.get('risk_level') == 'danger']
    warning_attachments = [att for att in attachments if att.get('risk_level') == 'warning']

    score = 10
    verdict = 'safe'
    notes = []

    if dangerous_attachments:
        score = 100
        verdict = 'malicious'
        notes.append('Обнаружены вложения с уровнем "danger"')
    elif warning_attachments:
        score = 65
        verdict = 'suspicious'
        notes.append('Вложения помечены как "warning"')

    if detected_keywords and score < 80:
        score = max(score, 60)
        verdict = 'suspicious'
        notes.append('Найдены фишинговые ключевые слова')

    non_https_links = [link for link in links if link.startswith('http://')]
    if non_https_links and score < 80:
        score = max(score, 55)
        verdict = 'suspicious'
        notes.append('Обнаружены небезопасные ссылки (HTTP)')

    details = {
        'attachments': attachments,
        'links': links,
        'suspicious_keywords': detected_keywords,
        'non_https_links': non_https_links,
        'notes': notes,
        'fallback': True
    }

    return {
        'verdict': verdict,
        'score': score,
        'details': details,
        'success': False,
        'source': 'fallback'
    }