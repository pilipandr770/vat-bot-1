# 🔐 File Scanner Module - Email Security for MailGuard

Микросервис для анализа безопасности email-сообщений с интеграцией VirusTotal API.

---

## 📋 Возможности

✅ **Анализ текста** - детекция подозрительных ключевых слов (фишинг, скам)  
✅ **Проверка ссылок** - обнаружение HTTP (не HTTPS), коротких URL  
✅ **Сканирование вложений** - анализ расширений файлов + VirusTotal  
✅ **VirusTotal интеграция** - 70+ антивирусных движков  
✅ **Fallback режим** - локальная эвристика если API недоступен  
✅ **JSON API** - готов для интеграции с MailGuard  

---

## 🚀 Быстрый старт

### 1. Установка зависенсий

```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

**Создайте `.env` файл:**

```bash
# Security Scanner Configuration
FILE_SCANNER_URL=https://vat-bot-1.onrender.com/file-scanner/api/email-scan
FILE_SCANNER_ENABLED=true
FILE_SCANNER_TOKEN=your-secure-token-here
VIRUSTOTAL_API_KEY=7977663b17d01aade4620f45d557de21525b7a67e91e21986ac2fb5f85574e66
```

**Генерация токена:**

```python
import secrets
print(secrets.token_urlsafe(32))
# Пример: dR8vK3p9wN2xQ7mL5fY6bC1aH4zT0sU8
```

### 3. Запуск локально

```bash
flask run --debug
```

Эндпоинт доступен на: `http://localhost:5000/file-scanner/api/email-scan`

---

## 📡 API Reference

### POST `/file-scanner/api/email-scan`

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <FILE_SCANNER_TOKEN>
```

**Request Body:**
```json
{
  "source": "mailguard",
  "content": {
    "text": "Email body text",
    "html": "<html>Email HTML</html>",
    "subject": "Email subject",
    "links": ["https://example.com"]
  },
  "attachments": [
    {
      "filename": "document.pdf",
      "content_type": "application/pdf",
      "temp_path": "/tmp/tmpfile123",
      "size": 102400
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "verdict": "safe",
  "score": 15,
  "details": {
    "text_analysis": {},
    "link_analysis": {},
    "attachment_analysis": [{
      "filename": "document.pdf",
      "risk": "safe",
      "virustotal": {
        "malicious": 0,
        "total": 71
      }
    }]
  }
}
```

**Verdict Types:**
- `safe` - безопасно (score 0-39)
- `suspicious` - подозрительно (score 40-69)
- `malicious` - опасно (score 70-100)

---

## 🔍 Детекция угроз

### Подозрительные ключевые слова

- überweisen, zahlung dringend, bitcoin
- passwort zurücksetzen, account suspended
- invoice attached, payment required
- verify your account, urgent action required

### Опасные расширения файлов

**Danger** (score +50, verdict: malicious):
- exe, dll, bat, cmd, vbs, js, jar, scr, pif, com

**Warning** (score +20, verdict: suspicious):
- zip, rar, 7z, gz, tar, iso

### Анализ ссылок

- HTTP ссылки (не HTTPS): +15 баллов
- Сокращённые URL (bit.ly, tinyurl.com): +10 баллов
- 3+ HTTP ссылок → auto-upgrade to `suspicious`

---

## 🛠️ Развёртывание на Render

### Шаг 1: Настройка переменных окружения

В Render Dashboard → Settings → Environment:

```
FILE_SCANNER_URL=https://vat-bot-1.onrender.com/file-scanner/api/email-scan
FILE_SCANNER_ENABLED=true
FILE_SCANNER_TOKEN=<generate-with-secrets.token_urlsafe(32)>
VIRUSTOTAL_API_KEY=7977663b17d01aade4620f45d557de21525b7a67e91e21986ac2fb5f85574e66
OPENAI_API_KEY=<your-openai-key>
MAILGUARD_ENCRYPTION_KEY=<generate-with-Fernet.generate_key()>
```

### Шаг 2: Проверка деплоя

```bash
# Push to GitHub (triggers auto-deploy)
git push origin main

# Check logs in Render dashboard
# Wait for "Starting gunicorn" message
```

### Шаг 3: Тестирование

```bash
curl -X POST https://vat-bot-1.onrender.com/file-scanner/api/email-scan \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "source": "test",
    "content": {
      "subject": "Test email",
      "text": "This is a test",
      "links": []
    },
    "attachments": []
  }'
```

**Ожидаемый результат:**
```json
{
  "success": true,
  "verdict": "safe",
  "score": 0
}
```

---

## 🔄 Интеграция с MailGuard

Модуль `scanner_client.py` автоматически вызывает эндпоинт при обработке email:

```python
# app/mailguard/tasks.py
from app.mailguard.scanner_client import scan_message

def create_draft_reply(message_id):
    message = MailMessage.query.get(message_id)
    
    # Сканируем email перед генерацией ответа
    scan_result = scan_message({
        'text': message.body_text,
        'html': message.body_html,
        'subject': message.subject,
        'attachments': message.attachments
    })
    
    if scan_result['verdict'] == 'malicious':
        # Не генерируем AI ответ, помечаем как опасное
        message.is_dangerous = True
        db.session.commit()
        return
    
    # Генерируем AI ответ с учётом результатов сканирования
    ai_reply = generate_ai_reply(message, scan_context=scan_result)
```

---

## 📊 VirusTotal API

### Лимиты Free Tier

- **500 запросов/день**
- **4 запроса/минуту**
- Файлы до **32 MB**

### Оптимизация запросов

1. **Hash lookup первым** - проверяем SHA256 хеш (быстро, без загрузки файла)
2. **Загрузка только новых файлов** - если хеш не найден
3. **Кэширование результатов** - избегаем повторных запросов

### Получение API ключа

1. Регистрация: https://www.virustotal.com/gui/join-us
2. API Key: https://www.virustotal.com/gui/my-apikey
3. Добавить в `.env`: `VIRUSTOTAL_API_KEY=<your-key>`

---

## 🐛 Troubleshooting

### Ошибка: "FILE_SCANNER_URL not configured"

**Решение:** Добавить в `.env`:
```bash
FILE_SCANNER_URL=https://vat-bot-1.onrender.com/file-scanner/api/email-scan
FILE_SCANNER_ENABLED=true
```

### Ошибка: "Unauthorized" (401)

**Решение:** Проверить токен в заголовке:
```bash
Authorization: Bearer <FILE_SCANNER_TOKEN>
```

### Ошибка: "VirusTotal API key not configured"

**Решение:** Добавить в `.env`:
```bash
VIRUSTOTAL_API_KEY=<your-virustotal-key>
```

### Fallback mode активирован

**Причина:** Внешний API недоступен  
**Решение:** Проверить:
1. `FILE_SCANNER_URL` правильный
2. Токен `FILE_SCANNER_TOKEN` совпадает
3. Сервис на Render запущен (проверить logs)

---

## 📚 Документация

- [API Reference](./EMAIL_SCAN_API.md) - полная спецификация API
- [Architecture](./ARCHITECTURE.md) - архитектура системы
- [Security Guide](./SECURITY.md) - руководство по безопасности

---

## 🧪 Тестирование

### Unit Tests

```bash
pytest tests/test_file_scanner.py -v
```

### Integration Tests

```bash
# Локальный тест
python -m app.mailguard.scanner_client

# Тест на production
curl -X POST https://vat-bot-1.onrender.com/file-scanner/api/email-scan \
  -H "Authorization: Bearer $FILE_SCANNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d @test_email.json
```

### Test Data

**test_email.json:**
```json
{
  "source": "test",
  "content": {
    "subject": "URGENT: Transfer bitcoin immediately",
    "text": "Please transfer payment to wallet...",
    "links": ["http://suspicious-site.com"]
  },
  "attachments": []
}
```

**Ожидаемый результат:**
```json
{
  "verdict": "suspicious",
  "score": 45
}
```

---

## 📈 Monitoring

### Логи на Render

```bash
# Посмотреть последние логи
render logs -f

# Фильтр по scanner
render logs | grep scanner
```

### Key Metrics

- **Scan requests per day** - количество запросов
- **VirusTotal API usage** - использование квоты (500/day)
- **Fallback rate** - % запросов в fallback mode
- **Average scan time** - среднее время сканирования

---

## 🔮 Roadmap

- [ ] Кэширование результатов сканирования (Redis)
- [ ] Rate limiting (предотвращение DDoS)
- [ ] Webhook notifications (Slack/Telegram при malicious)
- [ ] Batch scanning API (несколько файлов за раз)
- [ ] Machine Learning классификатор (обучение на истории)
- [ ] Quarantine storage (изоляция опасных файлов)

---

## 📝 License

MIT License - See [LICENSE](../LICENSE) file

---

## 👥 Contributors

- **Developer:** GitHub Copilot + pilipandr770
- **Project:** VAT Bot - Counterparty Verification System
- **Module:** MailGuard Email Intelligence

---

**Last Updated:** November 11, 2025  
**Version:** 1.0.0  
**Status:** ✅ Production-ready on Render
