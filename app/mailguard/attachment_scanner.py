"""
MailGuard Attachment Scanner - Проверка вложений ДО скачивания
Использует VirusTotal API для сканирования файлов в памяти (server-side)
"""
import hashlib
import base64
import io
import requests
import logging
from flask import current_app
from datetime import datetime

logger = logging.getLogger(__name__)


class AttachmentScanner:
    """
    Сканирование вложений Gmail на сервере (в памяти, без сохранения на диск)
    
    Workflow:
    1. Декодирует base64 вложение в bytes (в памяти)
    2. Вычисляет SHA256 хеш
    3. Проверяет VirusTotal по хешу (мгновенно если файл известен)
    4. Если не найден → загружает на VirusTotal для сканирования
    5. Возвращает результат с уровнем риска
    """
    
    # Подозрительные расширения файлов
    DANGEROUS_EXTENSIONS = [
        '.exe', '.dll', '.bat', '.cmd', '.scr', '.pif', '.com', '.vbs', 
        '.js', '.jar', '.app', '.deb', '.pkg', '.dmg', '.sh', '.ps1',
        '.msi', '.cpl', '.hta', '.wsf', '.vb', '.reg'
    ]
    
    # Подозрительные MIME типы
    DANGEROUS_MIMES = [
        'application/x-msdownload',
        'application/x-msdos-program',
        'application/x-executable',
        'application/x-dosexec',
        'application/x-sh',
        'application/x-bat'
    ]
    
    # Максимальный размер для загрузки на VirusTotal (32MB)
    VT_MAX_SIZE = 32 * 1024 * 1024
    
    def __init__(self):
        """Инициализация с API ключом из конфигурации"""
        self.vt_api_key = current_app.config.get('VIRUSTOTAL_API_KEY')
        self.vt_base_url = 'https://www.virustotal.com/api/v3'
    
    def scan_gmail_attachment(self, attachment_data_b64, filename, mime_type, size=None):
        """
        Сканировать вложение из Gmail API
        
        Args:
            attachment_data_b64 (str): base64 encoded attachment data from Gmail
            filename (str): Original filename
            mime_type (str): MIME type
            size (int, optional): File size in bytes
        
        Returns:
            dict: {
                'is_safe': bool or None (None if pending),
                'risk_level': 'safe'|'warning'|'danger',
                'threats': [list of threat names],
                'scan_details': {detailed scan info},
                'scanned_at': ISO timestamp,
                'sha256': file hash
            }
        """
        scan_start = datetime.utcnow()
        
        try:
            logger.info(f"Starting scan for attachment: {filename} ({mime_type})")
            
            # 1. Декодируем base64 в bytes (в памяти, НЕ на диск!)
            try:
                file_bytes = base64.urlsafe_b64decode(attachment_data_b64)
            except Exception as e:
                logger.error(f"Failed to decode base64 for {filename}: {e}")
                return self._error_result(f"Ошибка декодирования файла: {e}")
            
            file_size = len(file_bytes)
            logger.info(f"Decoded {filename}: {file_size} bytes")
            
            # 2. Быстрая эвристическая проверка (расширение, MIME, размер)
            quick_check = self._quick_scan(filename, mime_type, file_size)
            
            # Если файл явно опасен - не тратим API запросы
            if quick_check['risk_level'] == 'danger' and quick_check.get('block_immediately'):
                logger.warning(f"File {filename} blocked by quick scan: {quick_check['threats']}")
                return quick_check
            
            # 3. Вычисляем SHA256 хеш
            sha256_hash = hashlib.sha256(file_bytes).hexdigest()
            logger.info(f"SHA256 hash for {filename}: {sha256_hash}")
            
            # 4. Проверяем VirusTotal по хешу (БЕЗ загрузки файла)
            vt_result = self._check_virustotal_hash(sha256_hash)
            
            if vt_result['found']:
                # Хеш найден в VirusTotal - объединяем результаты
                logger.info(f"VirusTotal hash found for {filename}: {vt_result['malicious']}/{vt_result['total']}")
                final_result = self._parse_vt_result(vt_result, quick_check, sha256_hash)
                final_result['scanned_at'] = scan_start.isoformat()
                return final_result
            
            # 5. Хеш не найден - загружаем на VirusTotal (если размер допустимый)
            if file_size > self.VT_MAX_SIZE:
                logger.warning(f"File {filename} too large for VirusTotal: {file_size} bytes")
                result = quick_check.copy()
                result['sha256'] = sha256_hash
                result['scan_details'] = {
                    'message': f'Файл слишком большой для глубокого сканирования ({file_size / (1024*1024):.1f} MB)',
                    'quick_scan_only': True
                }
                result['scanned_at'] = scan_start.isoformat()
                return result
            
            # Загружаем файл на VirusTotal
            logger.info(f"Uploading {filename} to VirusTotal for analysis")
            vt_upload = self._upload_to_virustotal(file_bytes, filename)
            
            if vt_upload.get('success'):
                # Файл загружен, но результат будет позже (async)
                result = quick_check.copy()
                result['sha256'] = sha256_hash
                result['is_safe'] = None  # Pending
                result['scan_details'] = {
                    'status': 'pending',
                    'analysis_id': vt_upload.get('analysis_id'),
                    'message': 'Файл отправлен на глубокое сканирование (результат через 30-60 сек)'
                }
                result['scanned_at'] = scan_start.isoformat()
                return result
            else:
                # Ошибка загрузки - используем только quick scan
                logger.error(f"VirusTotal upload failed for {filename}: {vt_upload.get('error')}")
                result = quick_check.copy()
                result['sha256'] = sha256_hash
                result['scan_details'] = {
                    'virustotal_error': vt_upload.get('error'),
                    'quick_scan_only': True
                }
                result['scanned_at'] = scan_start.isoformat()
                return result
        
        except Exception as e:
            logger.error(f"Attachment scan error for {filename}: {e}", exc_info=True)
            return self._error_result(str(e))
    
    def _quick_scan(self, filename, mime_type, file_size):
        """
        Быстрая эвристическая проверка без внешних API
        
        Проверяет:
        - Опасные расширения (.exe, .bat, etc)
        - Двойные расширения (.pdf.exe)
        - Подозрительные MIME типы
        - Аномальные размеры файлов
        """
        risk_level = 'safe'
        threats = []
        block_immediately = False
        
        filename_lower = filename.lower()
        
        # 1. Проверка опасных расширений
        for ext in self.DANGEROUS_EXTENSIONS:
            if filename_lower.endswith(ext):
                risk_level = 'danger'
                threats.append(f'Исполняемый файл: {ext}')
                block_immediately = True  # Блокируем сразу
                break
        
        # 2. Проверка двойных расширений (.pdf.exe, .docx.bat)
        if filename.count('.') > 1:
            parts = filename_lower.split('.')
            if len(parts) >= 2:
                # Проверяем последнее расширение
                last_ext = f'.{parts[-1]}'
                second_last_ext = f'.{parts[-2]}'
                
                if last_ext in self.DANGEROUS_EXTENSIONS:
                    risk_level = 'danger'
                    threats.append(f'Двойное расширение: {second_last_ext}{last_ext} - возможная маскировка')
                    block_immediately = True
        
        # 3. Проверка подозрительных MIME типов
        if mime_type in self.DANGEROUS_MIMES:
            risk_level = 'danger'
            threats.append(f'Опасный MIME type: {mime_type}')
            block_immediately = True
        
        # 4. Проверка размера файла
        if file_size < 100:  # Слишком маленький (возможно дроппер)
            if risk_level != 'danger':
                risk_level = 'warning'
            threats.append('Подозрительно маленький размер файла')
        
        if file_size > 100 * 1024 * 1024:  # > 100MB
            if risk_level == 'safe':
                risk_level = 'warning'
            threats.append(f'Необычно большой файл: {file_size / (1024*1024):.1f} MB')
        
        # 5. Проверка на пробелы в конце имени (трюк для маскировки)
        if filename != filename.rstrip():
            if risk_level == 'safe':
                risk_level = 'warning'
            threats.append('Пробелы в конце имени файла - возможная маскировка')
        
        return {
            'is_safe': risk_level == 'safe',
            'risk_level': risk_level,
            'threats': threats if threats else ['Эвристический анализ не выявил угроз'],
            'scan_type': 'quick_heuristic',
            'block_immediately': block_immediately
        }
    
    def _check_virustotal_hash(self, sha256_hash):
        """
        Проверить хеш файла в VirusTotal БЕЗ загрузки самого файла
        
        Это экономит API quota - если файл уже сканировался, получаем результат мгновенно
        """
        if not self.vt_api_key:
            logger.warning("VirusTotal API key not configured")
            return {'found': False, 'error': 'API key not configured'}
        
        try:
            headers = {'x-apikey': self.vt_api_key}
            response = requests.get(
                f'{self.vt_base_url}/files/{sha256_hash}',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                stats = data['data']['attributes']['last_analysis_stats']
                
                # Извлекаем информацию об угрозах
                threats = self._extract_threat_names(data)
                
                return {
                    'found': True,
                    'malicious': stats.get('malicious', 0),
                    'suspicious': stats.get('suspicious', 0),
                    'undetected': stats.get('undetected', 0),
                    'total': sum(stats.values()),
                    'threats': threats,
                    'link': f'https://www.virustotal.com/gui/file/{sha256_hash}',
                    'last_analysis_date': data['data']['attributes'].get('last_analysis_date'),
                    'raw_stats': stats
                }
            elif response.status_code == 404:
                # Файл не найден в базе VirusTotal
                logger.info(f"Hash {sha256_hash} not found in VirusTotal")
                return {'found': False}
            else:
                logger.error(f"VirusTotal API error: {response.status_code} - {response.text}")
                return {'found': False, 'error': f'API error: {response.status_code}'}
        
        except requests.exceptions.Timeout:
            logger.error("VirusTotal API timeout")
            return {'found': False, 'error': 'Timeout'}
        except Exception as e:
            logger.error(f"VirusTotal hash check error: {e}", exc_info=True)
            return {'found': False, 'error': str(e)}
    
    def _upload_to_virustotal(self, file_bytes, filename):
        """
        Загрузить файл на VirusTotal для анализа
        
        Использует 1 API request из квоты (500/day на Free tier)
        Анализ занимает 30-60 секунд (async)
        """
        if not self.vt_api_key:
            return {'success': False, 'error': 'API key not configured'}
        
        try:
            headers = {'x-apikey': self.vt_api_key}
            files = {'file': (filename, io.BytesIO(file_bytes))}
            
            response = requests.post(
                f'{self.vt_base_url}/files',
                headers=headers,
                files=files,
                timeout=60  # Загрузка может занять время
            )
            
            if response.status_code == 200:
                data = response.json()
                analysis_id = data['data']['id']
                logger.info(f"File uploaded to VirusTotal: {analysis_id}")
                return {
                    'success': True,
                    'analysis_id': analysis_id,
                    'link': data['data']['links'].get('self')
                }
            else:
                logger.error(f"VirusTotal upload failed: {response.status_code} - {response.text}")
                return {'success': False, 'error': f'Upload failed: {response.status_code}'}
        
        except requests.exceptions.Timeout:
            logger.error("VirusTotal upload timeout")
            return {'success': False, 'error': 'Upload timeout'}
        except Exception as e:
            logger.error(f"VirusTotal upload error: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def _extract_threat_names(self, vt_data):
        """Извлечь имена обнаруженных угроз из VirusTotal результата"""
        threats = []
        try:
            results = vt_data['data']['attributes']['last_analysis_results']
            for engine_name, result in results.items():
                if result['category'] in ['malicious', 'suspicious']:
                    threat_name = result.get('result', 'Unknown')
                    threats.append(f"{engine_name}: {threat_name}")
        except Exception as e:
            logger.warning(f"Failed to extract threat names: {e}")
        
        # Ограничиваем до 10 самых важных
        return threats[:10]
    
    def _parse_vt_result(self, vt_result, quick_check, sha256_hash):
        """
        Объединить результаты VirusTotal и quick scan в финальный вердикт
        
        Logic:
        - detection_rate > 50% OR malicious > 10 → DANGER
        - detection_rate > 10% OR malicious > 2 → WARNING  
        - Иначе → SAFE (но учитываем quick_check)
        """
        malicious = vt_result.get('malicious', 0)
        suspicious = vt_result.get('suspicious', 0)
        total = vt_result.get('total', 1)
        
        detection_rate = (malicious + suspicious) / total if total > 0 else 0
        
        # Определяем уровень риска
        if detection_rate > 0.5 or malicious > 10:
            risk_level = 'danger'
            is_safe = False
        elif detection_rate > 0.1 or malicious > 2:
            risk_level = 'warning'
            is_safe = False
        else:
            # Может быть безопасен, но проверяем quick_check
            if quick_check['risk_level'] == 'danger':
                risk_level = 'danger'
                is_safe = False
            elif quick_check['risk_level'] == 'warning':
                risk_level = 'warning'
                is_safe = False
            else:
                risk_level = 'safe'
                is_safe = True
        
        # Объединяем угрозы
        all_threats = quick_check.get('threats', []) + vt_result.get('threats', [])
        
        return {
            'is_safe': is_safe,
            'risk_level': risk_level,
            'threats': all_threats[:15],  # Максимум 15 угроз
            'sha256': sha256_hash,
            'scan_details': {
                'virustotal': {
                    'malicious': malicious,
                    'suspicious': suspicious,
                    'undetected': vt_result.get('undetected', 0),
                    'total': total,
                    'detection_rate': f'{detection_rate * 100:.1f}%',
                    'link': vt_result.get('link'),
                    'last_analysis_date': vt_result.get('last_analysis_date')
                },
                'quick_scan': quick_check
            }
        }
    
    def _error_result(self, error_message):
        """Вернуть результат с ошибкой"""
        return {
            'is_safe': False,
            'risk_level': 'warning',
            'threats': ['Ошибка сканирования'],
            'scan_details': {
                'error': error_message
            },
            'scanned_at': datetime.utcnow().isoformat()
        }
    
    def check_analysis_status(self, analysis_id):
        """
        Проверить статус async анализа VirusTotal
        
        Используется для проверки результатов после загрузки файла
        """
        if not self.vt_api_key:
            return {'ready': False, 'error': 'API key not configured'}
        
        try:
            headers = {'x-apikey': self.vt_api_key}
            response = requests.get(
                f'{self.vt_base_url}/analyses/{analysis_id}',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data['data']['attributes']['status']
                
                if status == 'completed':
                    stats = data['data']['attributes']['stats']
                    return {
                        'ready': True,
                        'malicious': stats.get('malicious', 0),
                        'suspicious': stats.get('suspicious', 0),
                        'total': sum(stats.values())
                    }
                else:
                    return {'ready': False, 'status': status}
            else:
                return {'ready': False, 'error': f'API error: {response.status_code}'}
        
        except Exception as e:
            logger.error(f"Analysis status check error: {e}")
            return {'ready': False, 'error': str(e)}
