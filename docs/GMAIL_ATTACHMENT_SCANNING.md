# 🛡️ Gmail Attachment Scanning - Проверка вложений ДО скачивания

## 📋 Проблема

**Текущая реализация (`file_scanner`):**
- ✅ Работает с VirusTotal API
- ✅ Локальный анализ файлов
- ❌ **Требует скачивания файла на компьютер** → НЕБЕЗОПАСНО!
- ❌ Пользователь уже подвергается риску при скачивании

**Требуется:**
- Проверять вложения **на сервере** до того, как пользователь их скачает
- Интегрировать сканирование в MailGuard workflow
- Автоматически помечать опасные письма

---

## 🎯 Архитектура решения

### 1. Gmail API → Server-Side Scanning → User Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│                    Gmail API Workflow                        │
└─────────────────────────────────────────────────────────────┘

1. Email arrives → Gmail Push Notification
2. MailGuard fetches email metadata (subject, sender, attachments)
3. FOR EACH attachment:
   a) Download to server memory (BytesIO) - НЕ на диск!
   b) Calculate SHA256 hash
   c) Check VirusTotal by hash (instant if already scanned)
   d) If not found → Upload to VirusTotal for scanning
   e) Run local analysis (suspicious patterns)
   f) Store scan results in DB (ScanReport model)
4. Update MailMessage with scan status
5. If dangerous → Quarantine email + notify user
6. User sees scan results BEFORE clicking "Download"
```

---

## 🔧 Технические решения

### Option 1: VirusTotal API (Рекомендуется)
**Плюсы:**
- ✅ **70+ антивирусных движков** одновременно
- ✅ Мгновенные результаты по хешу (если файл уже сканировался)
- ✅ База данных угроз обновляется в реальном времени
- ✅ API v3 (уже используется в file_scanner)

**Минусы:**
- ❌ **Free tier: 500 requests/day** (может быть недостаточно)
- ❌ Premium: $600+/month для production

**Цена:**
- Free: 500 req/day, 4 req/min
- Premium: $192/month (15,000 req/day)
- Enterprise: Custom pricing

**API Usage:**
```python
# Проверка по хешу (БЕЗ загрузки файла)
GET https://www.virustotal.com/api/v3/files/{sha256}
→ Instant result if file was scanned before

# Если хеш не найден → загрузить файл
POST https://www.virustotal.com/api/v3/files
Content-Type: multipart/form-data
→ Returns analysis_id, wait 30-60 sec for results
```

---

### Option 2: ClamAV (Open Source, Self-Hosted)
**Плюсы:**
- ✅ **Бесплатный** и open-source
- ✅ Можно установить на сервер Render/AWS
- ✅ Обновляемые вирусные базы (freshclam)
- ✅ Python библиотека: `pyclamd` или `clamd`

**Минусы:**
- ❌ Требует установки на сервере (Docker container)
- ❌ Медленнее чем VirusTotal (1 движок vs 70)
- ❌ Может не распознать новые угрозы

**Docker Setup:**
```yaml
# docker-compose.yml
services:
  clamav:
    image: clamav/clamav:latest
    ports:
      - "3310:3310"
    volumes:
      - clamav-data:/var/lib/clamav
```

**Python Integration:**
```python
import clamd

cd = clamd.ClamdUnixSocket()
scan_result = cd.scan_stream(file_bytes)
```

---

### Option 3: Hybrid Approach (BEST)
Комбинация обоих методов для максимальной защиты:

1. **Быстрая проверка (1-2 секунды):**
   - ClamAV локально на сервере
   - Базовый фильтр подозрительных расширений
   - Проверка размера файла

2. **Глубокая проверка (30-60 секунд):**
   - VirusTotal API по хешу
   - Если хеш найден → мгновенный результат
   - Если нет → загрузить на сканирование

3. **Локальный анализ (уже реализован):**
   - Suspicious patterns (eval, exec, javascript:)
   - File size anomalies
   - Double extensions (.pdf.exe)

---

## 💻 Пример реализации

### 1. Создать модуль `app/mailguard/attachment_scanner.py`

```python
import hashlib
import base64
import io
import requests
from flask import current_app

class AttachmentScanner:
    """Сканирование вложений Gmail на сервере (в памяти)"""
    
    def __init__(self):
        self.vt_api_key = current_app.config.get('VIRUSTOTAL_API_KEY')
    
    def scan_gmail_attachment(self, attachment_data_b64, filename, mime_type):
        """
        Сканировать вложение из Gmail API
        
        Args:
            attachment_data_b64: base64 encoded attachment data from Gmail
            filename: original filename
            mime_type: MIME type
        
        Returns:
            {
                'is_safe': bool,
                'risk_level': 'safe|warning|danger',
                'threats': [...],
                'scan_details': {...}
            }
        """
        try:
            # Декодируем base64 в bytes (в памяти, НЕ на диск!)
            file_bytes = base64.urlsafe_b64decode(attachment_data_b64)
            file_size = len(file_bytes)
            
            # 1. Быстрая проверка
            quick_check = self._quick_scan(filename, mime_type, file_size)
            if quick_check['risk_level'] == 'danger':
                return quick_check
            
            # 2. Вычисляем SHA256 хеш
            sha256_hash = hashlib.sha256(file_bytes).hexdigest()
            
            # 3. Проверяем VirusTotal по хешу (БЕЗ загрузки)
            vt_result = self._check_virustotal_hash(sha256_hash)
            
            if vt_result['found']:
                return self._parse_vt_result(vt_result, quick_check)
            
            # 4. Если хеш не найден → загружаем на VirusTotal
            # ВАЖНО: Только если размер < 32MB
            if file_size < 32 * 1024 * 1024:
                vt_upload = self._upload_to_virustotal(file_bytes, filename)
                return {
                    'is_safe': None,  # Pending
                    'risk_level': quick_check['risk_level'],
                    'message': 'Файл отправлен на глубокое сканирование (30-60 сек)',
                    'analysis_id': vt_upload.get('analysis_id')
                }
            
            # 5. Файл слишком большой для VirusTotal
            return quick_check
        
        except Exception as e:
            current_app.logger.error(f"Attachment scan error: {e}")
            return {
                'is_safe': False,
                'risk_level': 'warning',
                'threats': [],
                'error': str(e)
            }
    
    def _quick_scan(self, filename, mime_type, file_size):
        """Быстрая эвристическая проверка"""
        risk_level = 'safe'
        threats = []
        
        # Подозрительные расширения
        dangerous_extensions = ['.exe', '.dll', '.bat', '.cmd', '.scr', '.pif', '.com', '.vbs', '.js']
        if any(filename.lower().endswith(ext) for ext in dangerous_extensions):
            risk_level = 'danger'
            threats.append(f'Исполняемый файл: {filename}')
        
        # Двойные расширения (.pdf.exe)
        if filename.count('.') > 1:
            parts = filename.split('.')
            if f'.{parts[-1]}' in dangerous_extensions:
                risk_level = 'danger'
                threats.append('Двойное расширение - возможная маскировка')
        
        # Подозрительные MIME типы
        dangerous_mimes = [
            'application/x-msdownload',
            'application/x-msdos-program',
            'application/x-executable'
        ]
        if mime_type in dangerous_mimes:
            risk_level = 'danger'
            threats.append(f'Опасный MIME type: {mime_type}')
        
        # Слишком большой файл
        if file_size > 100 * 1024 * 1024:  # 100MB
            risk_level = 'warning'
            threats.append('Необычно большой файл')
        
        return {
            'is_safe': risk_level == 'safe',
            'risk_level': risk_level,
            'threats': threats,
            'scan_type': 'quick_heuristic'
        }
    
    def _check_virustotal_hash(self, sha256_hash):
        """Проверить хеш в VirusTotal (БЕЗ загрузки файла)"""
        if not self.vt_api_key:
            return {'found': False, 'error': 'API key not configured'}
        
        try:
            headers = {'x-apikey': self.vt_api_key}
            response = requests.get(
                f'https://www.virustotal.com/api/v3/files/{sha256_hash}',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                stats = data['data']['attributes']['last_analysis_stats']
                
                return {
                    'found': True,
                    'malicious': stats.get('malicious', 0),
                    'suspicious': stats.get('suspicious', 0),
                    'total': stats.get('total', 0),
                    'link': f'https://www.virustotal.com/gui/file/{sha256_hash}',
                    'raw_data': data
                }
            
            return {'found': False}
        
        except Exception as e:
            current_app.logger.error(f"VirusTotal hash check error: {e}")
            return {'found': False, 'error': str(e)}
    
    def _upload_to_virustotal(self, file_bytes, filename):
        """Загрузить файл на VirusTotal для анализа"""
        if not self.vt_api_key:
            return {'success': False, 'error': 'API key not configured'}
        
        try:
            headers = {'x-apikey': self.vt_api_key}
            files = {'file': (filename, io.BytesIO(file_bytes))}
            
            response = requests.post(
                'https://www.virustotal.com/api/v3/files',
                headers=headers,
                files=files,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'analysis_id': data['data']['id']
                }
            
            return {'success': False, 'error': f'Upload failed: {response.status_code}'}
        
        except Exception as e:
            current_app.logger.error(f"VirusTotal upload error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _parse_vt_result(self, vt_result, quick_check):
        """Объединить результаты VirusTotal и quick scan"""
        malicious = vt_result.get('malicious', 0)
        total = vt_result.get('total', 1)
        detection_rate = malicious / total if total > 0 else 0
        
        if detection_rate > 0.5 or malicious > 10:
            risk_level = 'danger'
            is_safe = False
        elif detection_rate > 0.1 or malicious > 2:
            risk_level = 'warning'
            is_safe = False
        else:
            risk_level = 'safe'
            is_safe = True
        
        return {
            'is_safe': is_safe,
            'risk_level': risk_level,
            'threats': quick_check['threats'],
            'virustotal': {
                'malicious': malicious,
                'suspicious': vt_result.get('suspicious', 0),
                'total': total,
                'detection_rate': f'{detection_rate * 100:.1f}%',
                'link': vt_result.get('link')
            }
        }
```

---

### 2. Интегрировать в Gmail Connector

Обновить `app/mailguard/connectors/gmail.py`:

```python
def extract_attachments(service, message):
    """Извлечь вложения + СКАНИРОВАТЬ на сервере"""
    from ..attachment_scanner import AttachmentScanner
    
    scanner = AttachmentScanner()
    attachments = []

    def extract_from_parts(parts):
        for part in parts:
            if part.get('filename') and 'attachmentId' in part.get('body', {}):
                attachment_id = part['body']['attachmentId']
                filename = part['filename']
                mime_type = part.get('mimeType', '')
                size = part['body'].get('size', 0)

                try:
                    # Скачиваем вложение В ПАМЯТЬ (base64)
                    attachment = service.users().messages().attachments().get(
                        userId='me',
                        messageId=message['id'],
                        id=attachment_id
                    ).execute()

                    data_b64 = attachment['data']
                    
                    # СКАНИРУЕМ НА СЕРВЕРЕ
                    scan_result = scanner.scan_gmail_attachment(
                        attachment_data_b64=data_b64,
                        filename=filename,
                        mime_type=mime_type
                    )
                    
                    attachments.append({
                        'filename': filename,
                        'content_type': mime_type,
                        'size': size,
                        'data': data_b64,  # Сохраняем base64 для дальнейшей загрузки
                        'scan_result': scan_result,  # ← НОВОЕ!
                        'is_safe': scan_result['is_safe'],
                        'risk_level': scan_result['risk_level']
                    })

                except Exception as e:
                    current_app.logger.error(f"Error scanning attachment {filename}: {e}")
                    attachments.append({
                        'filename': filename,
                        'content_type': mime_type,
                        'size': size,
                        'scan_result': {'error': str(e)},
                        'is_safe': False,
                        'risk_level': 'warning'
                    })

            elif 'parts' in part:
                extract_from_parts(part['parts'])

    if 'payload' in message and 'parts' in message['payload']:
        extract_from_parts(message['payload']['parts'])

    return attachments
```

---

### 3. Обновить MailMessage Model

Добавить поле для хранения scan results в `app/mailguard/models.py`:

```python
class MailMessage(db.Model):
    __tablename__ = 'mail_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    # ... existing fields ...
    
    # NEW: Attachment scan results
    attachments_json = db.Column(db.Text)  # JSON array of attachments with scan results
    has_dangerous_attachments = db.Column(db.Boolean, default=False)
    is_quarantined = db.Column(db.Boolean, default=False)
    quarantine_reason = db.Column(db.String(500))
```

---

### 4. Dashboard UI - Показать статус сканирования

Обновить `templates/mailguard/inbox.html`:

```html
<div class="email-message" data-message-id="{{ message.id }}">
    <div class="email-header">
        <strong>{{ message.from_email }}</strong>
        <span class="email-subject">{{ message.subject }}</span>
        
        <!-- ATTACHMENT SECURITY BADGE -->
        {% if message.attachments_json %}
            {% set attachments = message.attachments_json|from_json %}
            {% for attachment in attachments %}
                <span class="badge badge-{{ 'danger' if attachment.risk_level == 'danger' else 'warning' if attachment.risk_level == 'warning' else 'success' }}">
                    {% if attachment.risk_level == 'danger' %}
                        🚨 ОПАСНО: {{ attachment.filename }}
                    {% elif attachment.risk_level == 'warning' %}
                        ⚠️ Подозрительно: {{ attachment.filename }}
                    {% else %}
                        ✅ Безопасно: {{ attachment.filename }}
                    {% endif %}
                </span>
            {% endfor %}
        {% endif %}
        
        <!-- QUARANTINE WARNING -->
        {% if message.is_quarantined %}
            <span class="badge badge-danger">
                🔒 В КАРАНТИНЕ: {{ message.quarantine_reason }}
            </span>
        {% endif %}
    </div>
    
    <!-- ATTACHMENT DOWNLOAD CONTROLS -->
    {% if message.attachments_json %}
        <div class="attachments-section">
            {% for attachment in attachments %}
                <div class="attachment-item">
                    <span class="attachment-icon">📎</span>
                    <span class="attachment-name">{{ attachment.filename }}</span>
                    <span class="attachment-size">{{ attachment.size|filesizeformat }}</span>
                    
                    {% if attachment.is_safe %}
                        <button class="btn btn-sm btn-success" onclick="downloadAttachment({{ message.id }}, {{ loop.index0 }})">
                            ⬇️ Скачать
                        </button>
                    {% else %}
                        <button class="btn btn-sm btn-danger" disabled>
                            🚫 Заблокировано
                        </button>
                        <small class="text-danger">
                            Причина: {{ attachment.scan_result.threats|join(', ') }}
                        </small>
                    {% endif %}
                </div>
            {% endfor %}
        </div>
    {% endif %}
</div>
```

---

## 📊 Workflow Example

### User Experience:

1. **Email arrives** → MailGuard auto-fetches
2. **Attachments scanned** on server (user doesn't see this)
3. **Dashboard shows result:**

```
📧 От: supplier@example.com
📋 Тема: Invoice #12345
📎 Вложения:
   ✅ invoice.pdf (245 KB) - Безопасно [Скачать]
   🚨 payment.exe (12 KB) - ОПАСНО! [Заблокировано]
      Обнаружено: 45/70 антивирусов
      Угрозы: Trojan.Generic, Malware.Heuristic
```

4. **User can:**
   - Download safe attachments
   - See detailed scan report
   - Manually override quarantine (admin only)

---

## 🔐 Security Benefits

### Before (Current):
1. User clicks "Download" in Gmail
2. File downloads to computer
3. **User already at risk!**
4. Manual scan with file_scanner
5. If dangerous → too late

### After (Proposed):
1. Email arrives → Auto-scan on server
2. Dangerous files **never reach user's computer**
3. User sees clear warning before any action
4. Safe files download instantly
5. Suspicious files → quarantine

---

## 💰 Cost Estimation

### Option 1: VirusTotal Only
- **Free tier**: 500 scans/day = ~15,000/month
- **Good for**: 10-20 users with moderate email volume
- **Upgrade**: $192/month for 15,000 scans/day

### Option 2: ClamAV Only
- **Free**: Open source, no API limits
- **Cost**: Server resources (Docker container)
- **Render.com**: ~$7/month for additional RAM

### Option 3: Hybrid (Recommended)
- **ClamAV**: Free local scanning
- **VirusTotal Free**: 500 deep scans/day for unknown files
- **Total cost**: $7/month (server) + Free (VirusTotal)

---

## 🚀 Implementation Priority

### Phase 1 (MVP - 2 days):
1. ✅ Create `attachment_scanner.py` module
2. ✅ Integrate basic VirusTotal API check
3. ✅ Update Gmail connector to scan attachments
4. ✅ Show scan results in dashboard

### Phase 2 (Enhanced - 1 week):
1. 🔄 Add ClamAV Docker container
2. 🔄 Implement hybrid scanning
3. 🔄 Auto-quarantine dangerous emails
4. 🔄 User notification system

### Phase 3 (Production - 2 weeks):
1. 📅 Background job for periodic re-scanning
2. 📅 Admin dashboard for quarantine management
3. 📅 User override controls with logging
4. 📅 Integration with CRM alerts

---

## 📝 Next Steps

### Immediate Actions:
1. **Decide on scanner**: VirusTotal, ClamAV, or Hybrid?
2. **Add VIRUSTOTAL_API_KEY** to `.env` (if not already)
3. **Create `attachment_scanner.py`** (code provided above)
4. **Update Gmail connector** to scan attachments
5. **Test with sample email** containing safe + dangerous attachments

### Questions to Answer:
- Сколько писем с вложениями в день ожидается?
- Какой бюджет на security scanning?
- Нужна ли поддержка других провайдеров (Microsoft, IMAP)?
- Нужно ли сканировать ВСЕ вложения или только подозрительные?

---

## 🔗 Related Files

- `file_scanner/routes.py` - Current local file scanner (reference)
- `app/mailguard/connectors/gmail.py` - Gmail API integration (update here)
- `app/mailguard/models.py` - Add attachment scan fields
- `app/mailguard/scanner.py` - Currently empty (use this file!)

---

**Author:** GitHub Copilot  
**Date:** November 7, 2025  
**Status:** Planning phase - awaiting user decision on implementation approach
