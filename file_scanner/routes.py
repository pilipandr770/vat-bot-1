import os
import tempfile
import hashlib
import requests
from flask import render_template, request, jsonify, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import logging

from . import file_scanner

logger = logging.getLogger(__name__)

# Разрешённые типы файлов для сканирования
ALLOWED_EXTENSIONS = {
    'exe', 'dll', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js', 'jar',
    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'zip', 'rar', '7z', 'tar', 'gz',
    'txt', 'rtf', 'html', 'xml', 'json'
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@file_scanner.route('/')
@login_required
def scan_page():
    """Страница сканера файлов"""
    return render_template('file_scanner/scan.html')

@file_scanner.route('/api/file-scan', methods=['POST'])
@login_required
def scan_file():
    """API для сканирования файла"""
    try:
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

        # Создаём временный файл для анализа
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{secure_filename(file.filename)}") as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name

        try:
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
            # Удаляем временный файл
            try:
                os.unlink(temp_path)
            except:
                pass

    except Exception as e:
        logger.error(f"Error scanning file: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Fehler beim Scannen der Datei'
        }), 500

def scan_with_virustotal(file_path, file_hash, filename):
    """Сканирование через VirusTotal API"""
    try:
        api_key = current_app.config.get('VIRUSTOTAL_API_KEY')
        if not api_key:
            return {
                'available': False,
                'error': 'VirusTotal API nicht konfiguriert'
            }

        # Сначала проверяем, есть ли уже результат для этого хэша
        headers = {'x-apikey': api_key}
        response = requests.get(f'https://www.virustotal.com/api/v3/files/{file_hash}', headers=headers)

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
            with open(file_path, 'rb') as f:
                files = {'file': (filename, f)}
                response = requests.post('https://www.virustotal.com/api/v3/files', headers=headers, files=files)

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
    """Локальный анализ файла"""
    analysis = {
        'suspicious_patterns': [],
        'file_properties': {},
        'risk_level': 'low'
    }

    try:
        # Проверяем размер файла
        file_size = os.path.getsize(file_path)
        analysis['file_properties']['size'] = file_size

        # Проверяем расширение
        if '.' in filename:
            ext = filename.rsplit('.', 1)[1].lower()
            analysis['file_properties']['extension'] = ext

            # Проверяем подозрительные комбинации
            suspicious_extensions = ['exe', 'bat', 'cmd', 'scr', 'pif', 'com']
            if ext in suspicious_extensions:
                analysis['suspicious_patterns'].append(f'Выполняемый файл ({ext})')
                analysis['risk_level'] = 'medium'

        # Проверяем на подозрительные строки в текстовых файлах
        if filename.lower().endswith(('.txt', '.js', '.html', '.xml', '.json')):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(1024)  # Проверяем только начало файла

                    suspicious_strings = [
                        'eval(', 'exec(', 'system(', 'shell_exec(',
                        'javascript:', 'vbscript:', 'data:',
                        '<script', 'onload=', 'onerror='
                    ]

                    for pattern in suspicious_strings:
                        if pattern.lower() in content.lower():
                            analysis['suspicious_patterns'].append(f'Подозрительная строка: {pattern}')
                            analysis['risk_level'] = 'high'
                            break

            except:
                pass

        # Для исполняемых файлов - повышенная осторожность
        if filename.lower().endswith(('.exe', '.dll', '.bat', '.cmd')):
            analysis['suspicious_patterns'].append('Исполняемый файл - требуется дополнительная проверка')
            analysis['risk_level'] = 'high'

    except Exception as e:
        logger.error(f"Local analysis error: {str(e)}")
        analysis['error'] = str(e)

    return analysis

def get_virus_names(data):
    """Извлекаем имена обнаруженных вирусов"""
    threats = []
    try:
        results = data['data']['attributes']['last_analysis_results']
        for engine, result in results.items():
            if result['category'] == 'malicious':
                threats.append(f"{engine}: {result['result']}")
    except:
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