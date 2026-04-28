import os
import tempfile
import hashlib
import requests
from flask import render_template, request, jsonify, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import logging
import shutil

from . import file_scanner

logger = logging.getLogger(__name__)

# Разрешённые типы файлов для сканирования
ALLOWED_EXTENSIONS = {
    'exe', 'dll', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js', 'jar',
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'zip', 'rar', '7z', 'tar', 'gz',
    'txt', 'rtf', 'html', 'xml', 'json'
}

# Запрещённые имена файлов (системные файлы)
FORBIDDEN_NAMES = {
    'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9',
    'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_CONCURRENT_SCANS = 3  # Максимум одновременных сканирований

# Счётчик активных сканирований
active_scans = 0

def allowed_file(filename):
    if not filename or '.' not in filename:
        return False

    name_part = filename.rsplit('.', 1)[0].lower()
    ext_part = filename.rsplit('.', 1)[1].lower()

    # Проверяем запрещённые имена
    if name_part in FORBIDDEN_NAMES:
        return False

    return ext_part in ALLOWED_EXTENSIONS

@file_scanner.route('/')
@login_required
def scan_page():
    """Страница сканера файлов"""
    return render_template('file_scanner/scan.html')

@file_scanner.route('/api/file-scan', methods=['POST'])
def scan_file():
    """API для сканирования файла"""
    global active_scans

    # Проверяем авторизацию по токену для сервисных вызовов
    expected_token = current_app.config.get('FILE_SCANNER_TOKEN')
    if expected_token:
        provided = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
        if not provided:
            provided = request.headers.get('X-Scanner-Token', '').strip()
        if provided != expected_token:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    else:
        # Без токена допускаем запросы только от авторизованных пользователей
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    # Проверяем лимит одновременных сканирований
    if active_scans >= MAX_CONCURRENT_SCANS:
        return jsonify({
            'success': False,
            'error': 'Zu viele gleichzeitige Scans. Bitte warten Sie.'
        }), 429

    try:
        active_scans += 1

        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Keine Datei ausgewählt'
            }), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Keine Datei ausgewählt'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'Nicht unterstützter Dateityp. Erlaubt: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400

        # Проверяем размер файла
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'error': f'Datei zu groß. Maximum: {MAX_FILE_SIZE // (1024*1024)}MB'
            }), 400

        # Создаём временный файл для анализа в системной temp директории
        temp_dir = tempfile.gettempdir()
        temp_fd, temp_path = tempfile.mkstemp(suffix=f"_scan_{secure_filename(file.filename)}", dir=temp_dir)
        os.close(temp_fd)  # Закрываем дескриптор, файл будет открыт заново

        try:
            # Сохраняем файл безопасно
            with open(temp_path, 'wb') as temp_file:
                shutil.copyfileobj(file, temp_file)

            # Вычисляем хэш файла
            sha256_hash = hashlib.sha256()
            with open(temp_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            file_hash = sha256_hash.hexdigest()

            # Сканируем файл через VirusTotal
            scan_result = scan_with_virustotal(temp_path, file_hash, file.filename)

            # Анализируем файл локально
            local_analysis = analyze_file_locally(temp_path, file.filename)

            # Комбинируем результаты
            result = {
                'success': True,
                'file_info': {
                    'name': file.filename,
                    'size': file_size,
                    'hash': file_hash,
                    'type': file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown'
                },
                'virustotal': scan_result,
                'local_analysis': local_analysis,
                'recommendation': get_recommendation(scan_result, local_analysis)
            }

            return jsonify(result)

        finally:
            # Гарантированное удаление временного файла
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except Exception as e:
                logger.error(f"Failed to delete temp file {temp_path}: {e}")
                # В крайнем случае попробуем удалить позже
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    except Exception as e:
        logger.error(f"Error scanning file: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Fehler beim Scannen der Datei'
        }), 500
    finally:
        active_scans -= 1


@file_scanner.route('/api/email-scan', methods=['POST'])
def scan_email():
    """
    API эндпоинт для сканирования email-сообщений от MailGuard.
    Принимает JSON с текстом, ссылками и вложениями.
    """
    # Проверяем авторизацию по токену
    expected_token = current_app.config.get('FILE_SCANNER_TOKEN')
    if expected_token:
        provided = request.headers.get('Authorization', '').replace('Bearer ', '').strip()
        if not provided:
            provided = request.headers.get('X-Scanner-Token', '').strip()
        if provided != expected_token:
            return jsonify({'success': False, 'error': 'Unauthorized', 'verdict': 'unknown', 'score': 0}), 401
    else:
        # Без токена допускаем запросы только от авторизованных пользователей
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Unauthorized', 'verdict': 'unknown', 'score': 0}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided',
                'verdict': 'unknown',
                'score': 0
            }), 400

        # Извлекаем данные из запроса
        source = data.get('source', 'mailguard')
        content = data.get('content', {})
        attachments = data.get('attachments', [])

        # Результаты проверки
        verdict = 'safe'
        score = 0
        details = {
            'text_analysis': {},
            'link_analysis': {},
            'attachment_analysis': [],
            'virustotal_results': []
        }

        # 1. Анализ текста на подозрительные ключевые слова
        text = content.get('text', '') or ''
        html = content.get('html', '') or ''
        subject = content.get('subject', '') or ''
        combined_text = f"{subject} {text} {html}".lower()

        suspicious_keywords = [
            'überweisen', 'zahlung dringend', 'bitcoin', 'passwort zurücksetzen',
            'invoice attached', 'payment required', 'account suspended', 'verify your account',
            'click here immediately', 'urgent action required', 'cryptocurrency', 'wallet address'
        ]

        detected_keywords = [kw for kw in suspicious_keywords if kw in combined_text]
        if detected_keywords:
            score += len(detected_keywords) * 10
            details['text_analysis']['suspicious_keywords'] = detected_keywords
            if len(detected_keywords) >= 3:
                verdict = 'suspicious'

        # 2. Анализ ссылок
        links = content.get('links', [])
        http_links = [link for link in links if link.startswith('http://')]
        suspicious_domains = ['bit.ly', 'tinyurl.com', 'goo.gl']  # Короткие ссылки
        shortened_links = [link for link in links if any(domain in link for domain in suspicious_domains)]

        if http_links:
            score += len(http_links) * 15
            details['link_analysis']['http_links'] = http_links
            if len(http_links) > 2:
                verdict = 'suspicious'

        if shortened_links:
            score += len(shortened_links) * 10
            details['link_analysis']['shortened_links'] = shortened_links

        # 3. Сканирование вложений через VirusTotal
        api_key = current_app.config.get('VIRUSTOTAL_API_KEY')
        
        for att in attachments:
            filename = att.get('filename', 'unknown')
            file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            temp_path = att.get('temp_path')
            file_size = att.get('size', 0)

            att_result = {
                'filename': filename,
                'size': file_size,
                'extension': file_ext,
                'risk': 'unknown'
            }

            # Опасные расширения
            dangerous_extensions = {'exe', 'dll', 'bat', 'cmd', 'vbs', 'js', 'jar', 'scr', 'pif', 'com'}
            warning_extensions = {'zip', 'rar', '7z', 'gz', 'tar', 'iso'}

            if file_ext in dangerous_extensions:
                score += 50
                verdict = 'malicious'
                att_result['risk'] = 'danger'
                att_result['reason'] = f'Dangerous file extension: .{file_ext}'
            elif file_ext in warning_extensions:
                score += 20
                if verdict == 'safe':
                    verdict = 'suspicious'
                att_result['risk'] = 'warning'
                att_result['reason'] = f'Archive file: .{file_ext}'

            # Проверяем через VirusTotal если есть temp_path и API ключ
            if temp_path and os.path.exists(temp_path) and api_key:
                try:
                    # Вычисляем хеш
                    sha256_hash = hashlib.sha256()
                    with open(temp_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            sha256_hash.update(chunk)
                    file_hash = sha256_hash.hexdigest()

                    # Проверяем в VirusTotal
                    headers = {'x-apikey': api_key}
                    response = requests.get(
                        f'https://www.virustotal.com/api/v3/files/{file_hash}',
                        headers=headers,
                        timeout=10
                    )

                    if response.status_code == 200:
                        vt_data = response.json()
                        stats = vt_data['data']['attributes']['last_analysis_stats']
                        malicious_count = stats.get('malicious', 0)
                        total_engines = stats.get('total', 0)

                        att_result['virustotal'] = {
                            'malicious': malicious_count,
                            'total': total_engines,
                            'hash': file_hash,
                            'link': f'https://www.virustotal.com/gui/file/{file_hash}'
                        }

                        if malicious_count > 0:
                            score += malicious_count * 5
                            verdict = 'malicious'
                            att_result['risk'] = 'danger'
                            att_result['reason'] = f'VirusTotal: {malicious_count}/{total_engines} engines detected malware'
                        elif att_result.get('risk') == 'unknown':
                            att_result['risk'] = 'safe'

                except Exception as e:
                    logger.warning(f"VirusTotal check failed for {filename}: {e}")
                    att_result['virustotal_error'] = str(e)

            details['attachment_analysis'].append(att_result)

        # Нормализуем score (max 100)
        score = min(score, 100)

        # Финальный verdict
        if score >= 70:
            verdict = 'malicious'
        elif score >= 40:
            verdict = 'suspicious'
        else:
            verdict = 'safe'

        return jsonify({
            'success': True,
            'verdict': verdict,
            'score': score,
            'details': details,
            'source': 'file_scanner_email_api'
        })

    except Exception as e:
        logger.error(f"Email scan error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'verdict': 'unknown',
            'score': 0
        }), 500


def scan_with_virustotal(file_path, file_hash, filename):
    """Сканирование через VirusTotal API - ТОЛЬКО ЗАГРУЗКА, БЕЗ ВЫПОЛНЕНИЯ"""
    try:
        api_key = current_app.config.get('VIRUSTOTAL_API_KEY')
        if not api_key:
            return {
                'available': False,
                'error': 'VirusTotal API nicht konfiguriert'
            }

        # Проверяем размер файла перед отправкой (VirusTotal limit ~650MB, но мы ограничиваем)
        file_size = os.path.getsize(file_path)
        if file_size > 32 * 1024 * 1024:  # 32MB для VirusTotal
            return {
                'available': True,
                'scanned': False,
                'message': 'Datei zu groß für VirusTotal Upload. Verwenden Sie lokale Analyse.'
            }

        # Сначала проверяем, есть ли уже результат для этого хэша
        headers = {'x-apikey': api_key}
        response = requests.get(f'https://www.virustotal.com/api/v3/files/{file_hash}', headers=headers, timeout=10)

        if response.status_code == 200:
            # Файл уже сканировался
            data = response.json()
            stats = data['data']['attributes']['last_analysis_stats']
            return {
                'available': True,
                'scanned': True,
                'positives': stats.get('malicious', 0),
                'total': stats.get('total', 0),
                'threats': get_virus_names(data),
                'link': f'https://www.virustotal.com/gui/file/{file_hash}'
            }
        elif response.status_code == 404:
            # Файл не сканировался, загружаем для анализа
            try:
                with open(file_path, 'rb') as f:
                    files = {'file': (secure_filename(filename), f)}
                    response = requests.post('https://www.virustotal.com/api/v3/files',
                                           headers=headers, files=files, timeout=30)

                if response.status_code == 200:
                    analysis_id = response.json()['data']['id']
                    return {
                        'available': True,
                        'scanned': False,
                        'analysis_id': analysis_id,
                        'message': 'Datei wurde zur Analyse hochgeladen. Ergebnis wird in Kürze verfügbar sein.'
                    }
                else:
                    return {
                        'available': True,
                        'error': f'Upload fehlgeschlagen: {response.status_code}'
                    }
            except requests.exceptions.RequestException as e:
                return {
                    'available': True,
                    'error': f'Netzwerkfehler: {str(e)}'
                }
        else:
            return {
                'available': True,
                'error': f'API Fehler: {response.status_code}'
            }

    except Exception as e:
        logger.error(f"VirusTotal scan error: {str(e)}")
        return {
            'available': False,
            'error': f'VirusTotal Fehler: {str(e)}'
        }

def analyze_file_locally(file_path, filename):
    """Локальный анализ файла - ТОЛЬКО ЧТЕНИЕ, БЕЗ ВЫПОЛНЕНИЯ КОДА"""
    analysis = {
        'suspicious_patterns': [],
        'file_properties': {},
        'risk_level': 'low'
    }

    try:
        # Проверяем, что файл существует и доступен для чтения
        if not os.path.exists(file_path):
            analysis['error'] = 'Файл не найден'
            return analysis

        # Проверяем размер файла
        file_size = os.path.getsize(file_path)
        analysis['file_properties']['size'] = file_size

        # Проверяем расширение
        if '.' in filename:
            ext = filename.rsplit('.', 1)[1].lower()
            analysis['file_properties']['extension'] = ext

            # Проверяем подозрительные комбинации
            suspicious_extensions = ['exe', 'bat', 'cmd', 'scr', 'pif', 'com', 'dll']
            if ext in suspicious_extensions:
                analysis['suspicious_patterns'].append(f'Выполняемый файл ({ext}) - повышенная осторожность')
                analysis['risk_level'] = 'medium'

        # Проверяем на подозрительные строки ТОЛЬКО в текстовых файлах
        text_extensions = ['txt', 'js', 'html', 'xml', 'json', 'rtf']
        if any(filename.lower().endswith('.' + ext) for ext in text_extensions):
            try:
                # Читаем только первые 2048 байт для анализа
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(2048)

                    # Список подозрительных паттернов (только строковые)
                    suspicious_strings = [
                        'eval(', 'exec(', 'system(', 'shell_exec(', 'popen(',
                        'javascript:', 'vbscript:', 'data:',
                        '<script', 'onload=', 'onerror=', 'onmouseover=',
                        'document.cookie', 'localStorage', 'sessionStorage',
                        'innerHTML', 'outerHTML', 'insertAdjacentHTML'
                    ]

                    found_patterns = []
                    for pattern in suspicious_strings:
                        if pattern.lower() in content.lower():
                            found_patterns.append(pattern)

                    if found_patterns:
                        analysis['suspicious_patterns'].extend([f'Подозрительная строка: {p}' for p in found_patterns[:5]])  # Макс 5 паттернов
                        analysis['risk_level'] = 'high'

            except Exception as e:
                logger.warning(f"Error reading text file {filename}: {e}")
                analysis['suspicious_patterns'].append('Ошибка чтения файла')

        # Для исполняемых файлов - автоматическое повышение риска
        if filename.lower().endswith(('.exe', '.dll', '.bat', '.cmd', '.scr', '.pif', '.com')):
            analysis['suspicious_patterns'].append('Исполняемый файл - требует дополнительной проверки')
            analysis['risk_level'] = 'high'

        # Проверка на слишком маленький размер (может быть пустышкой)
        if file_size < 10:
            analysis['suspicious_patterns'].append('Файл слишком маленький')
            analysis['risk_level'] = 'medium'

    except Exception as e:
        logger.error(f"Local analysis error for {filename}: {str(e)}")
        analysis['error'] = f'Ошибка анализа: {str(e)}'
        analysis['risk_level'] = 'medium'

    return analysis

def get_virus_names(data):
    """Извлекаем имена обнаруженных вирусов"""
    threats = []
    try:
        results = data['data']['attributes']['last_analysis_results']
        for engine, result in results.items():
            if result['category'] == 'malicious':
                threats.append(f"{engine}: {result['result']}")
    except Exception:
        pass
    return threats[:10]  # Ограничиваем до 10 результатов

def get_recommendation(vt_result, local_analysis):
    """Формируем рекомендацию на основе результатов анализа"""
    risk_score = 0

    # Оцениваем результат VirusTotal
    if vt_result.get('available') and vt_result.get('scanned'):
        positives = vt_result.get('positives', 0)
        total = vt_result.get('total', 1)
        detection_rate = positives / total

        if detection_rate > 0.5:
            risk_score += 3
        elif detection_rate > 0.1:
            risk_score += 2
        elif positives > 0:
            risk_score += 1

    # Оцениваем локальный анализ
    if local_analysis.get('risk_level') == 'high':
        risk_score += 2
    elif local_analysis.get('risk_level') == 'medium':
        risk_score += 1

    # Формируем рекомендацию
    if risk_score >= 4:
        return {
            'level': 'danger',
            'action': 'delete',
            'message': '🚨 ВЫСОКИЙ РИСК! Немедленно удалите файл и проверьте систему антивирусом!'
        }
    elif risk_score >= 2:
        return {
            'level': 'warning',
            'action': 'quarantine',
            'message': '⚠️ ПОДОЗРИТЕЛЬНЫЙ ФАЙЛ! Рекомендуется поместить в карантин и проверить дополнительно.'
        }
    else:
        return {
            'level': 'success',
            'action': 'safe',
            'message': '✅ Файл безопасен. Можно открывать без опасений.'
        }