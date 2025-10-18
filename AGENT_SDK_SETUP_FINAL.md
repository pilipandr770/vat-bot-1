# 🚀 OpenAI Agents SDK Integration - Final Setup

## ✅ Що змінено

Ваш чатбот тепер використовує **правильний підхід** для Agent Builder:
- ✅ OpenAI Agents SDK замість прямих HTTP запитів
- ✅ Thread-based розмови (як в ChatGPT)
- ✅ Ваш workflow ID: `wf_68f3ed065d5881909c95b20ad801090b07e400bf50570e4d`
- ✅ Передача контексту користувача німецькою
- ✅ Детальне логування для діагностики

---

## 📋 Налаштування на Render Dashboard

### 1. Видаліть старі змінні (якщо є)
- ❌ `OPENAI_AGENT_API_KEY` - видалити
- ❌ `OPENAI_AGENT_API_URL` - видалити

### 2. Додайте нові змінні

Render Dashboard → Environment → Add Environment Variable:

```
OPENAI_API_KEY = sk-proj-ваш_ключ_тут
```

(Workflow ID вже в коді: `wf_68f3ed065d5881909c95b20ad801090b07e400bf50570e4d`)

**Де взяти API ключ?**
1. https://platform.openai.com/api-keys
2. Create new secret key
3. Скопіюйте (показується тільки раз!)

---

## 🤖 Налаштування System Prompt в Agent Builder

### Крок 1: Відкрийте ваш Agent в Agent Builder
1. https://platform.openai.com → Agent Builder
2. Знайдіть ваш workflow `wf_68f3ed065d5881909c95b20ad801090b07e400bf50570e4d`

### Крок 2: Скопіюйте System Instructions
Відкрийте файл **`AGENT_SYSTEM_PROMPT.md`** і скопіюйте весь вміст в секцію "System Instructions" або "Instructions" вашого агента.

Це дасть агенту знання про:
- ✅ Всі функції платформи (Dashboard, VAT Verification, OSINT Scanner)
- ✅ Як працює кожна функція
- ✅ Типові питання користувачів і відповіді
- ✅ Підтримувані країни та обмеження
- ✅ Ціни та підписки
- ✅ Юридичні сторінки

### Крок 3: Налаштуйте модель (опціонально)
- **Модель**: GPT-4 або GPT-4-turbo (рекомендовано)
- **Temperature**: 0.7 (баланс між точністю та креативністю)
- **Max tokens**: 1000-2000 (достатньо для детальних відповідей)

---

## 🧪 Тестування

### Локальний тест (опціонально)
```powershell
# Створіть .env файл
OPENAI_API_KEY=sk-proj-ваш_ключ

# Запустіть Flask
python app.py

# Відкрийте
http://localhost:5000/chatbot/chat
```

### Тест на Production
1. Зачекайте завершення deployment (~2-3 хв)
2. Відкрийте https://vat-bot-1.onrender.com/chatbot/chat
3. Спробуйте питання:
   - "Wie starte ich eine Prüfung?"
   - "Was macht der OSINT-Scanner?"
   - "Wie ändere ich mein Abo?"
   - "Welche Länder werden unterstützt?"

### Очікувані відповіді
Агент повинен давати **конкретні** відповіді німецькою з:
- Покроковими інструкціями
- URL-адресами (наприклад `/verify`, `/osint/scan`)
- Прикладами (формат USt-IdNr., etc.)
- Контекстом користувача (ім'я, план підписки)

---

## 📊 Моніторинг

### Render Logs
Тепер ви побачите детальні логи:
```
[CHATBOT] Using Agents SDK with workflow: wf_68f3ed065d5881909c95b20ad801090b07e400bf50570e4d
[CHATBOT] User message: Wie starte ich eine Prüfung?
[CHATBOT] Created thread: thread_abc123
[CHATBOT] Started run: run_xyz789
[CHATBOT] Run status: in_progress (elapsed: 2s)
[CHATBOT] Run status: completed (elapsed: 4s)
[CHATBOT] Success! Response length: 245 chars
```

### OpenAI Usage Dashboard
- https://platform.openai.com/usage
- Моніторте витрати (кожне повідомлення ~$0.01-$0.03)
- Встановіть billing alerts

---

## 🔧 Як це працює технічно

### Архітектура
```
User (Browser)
    ↓ POST /chatbot/api/chat/message
Flask (chatbot_routes.py)
    ↓ client.beta.threads.create()
OpenAI Agents API
    ↓ Your workflow wf_68f3ed...
GPT-4/5 Model + System Instructions
    ↓ Response
Flask → JSON
    ↓
User (Chat UI)
```

### Thread-based розмова
1. **Створюємо thread** - нова розмова
2. **Додаємо message** - питання користувача + контекст
3. **Запускаємо run** - викликаємо ваш workflow як assistant
4. **Polling** - чекаємо завершення (max 60s)
5. **Отримуємо відповідь** - останнє повідомлення асистента

### Контекст користувача
Передається німецькою в кожному запиті:
```
Benutzerkontext:
- E-Mail: user@example.com
- Name: John Doe
- Abonnement: Basic
- Administrator: Nein

Benutzeranfrage: Wie starte ich eine Prüfung?
```

Агент використовує це для персоналізованих відповідей.

---

## ❓ Troubleshooting

### Помилка: "API key not configured"
- Перевірте, чи `OPENAI_API_KEY` додано в Render Environment
- Redeploy сервіс після додавання змінної

### Помилка: "Assistant ID not found"
- Workflow ID `wf_68f3ed...` має бути валідним в OpenAI
- Перевірте, чи workflow активний в Agent Builder
- Можливо, потрібно використати інший ID (assistant_id замість workflow_id)

### Агент не розуміє питання
- Переконайтесь, що System Prompt скопійовано в Agent Builder
- Оновіть інструкції агента в платформі OpenAI
- Може потрібно час на синхронізацію (~5 хв)

### Timeout після 60 секунд
- Спростіть System Prompt (можливо, занадто довгий)
- Зменшіть max_tokens в Agent Builder
- Перевірте статус OpenAI API: https://status.openai.com

---

## 💰 Очікувані витрати

### За повідомлення
- **Input tokens** (System Prompt + User Message): ~1500-2000 tokens
- **Output tokens** (Agent Response): ~200-500 tokens
- **Вартість** (~GPT-4): $0.01-$0.03 на повідомлення

### Місячна оцінка
- **100 повідомлень**: ~$1-3
- **500 повідомлень**: ~$5-15
- **1000 повідомлень**: ~$10-30

**Рекомендація**: Встановіть billing limit $50/місяць для безпеки.

---

## 🎯 Наступні кроки (опціонально)

### 1. Збереження історії чатів
Додайте таблицю в БД для збереження thread_id та повідомлень:
```python
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    thread_id = db.Column(db.String(100))
    message = db.Column(db.Text)
    response = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
```

### 2. Rate limiting
Обмежте кількість повідомлень на користувача (наприклад, 20/годину):
```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: current_user.id)

@chatbot_bp.route("/api/chat/message", methods=["POST"])
@limiter.limit("20 per hour")
@login_required
def send_message():
    ...
```

### 3. Feedback система
Додайте кнопки "👍 Hilfreich" / "👎 Nicht hilfreich" для покращення агента.

### 4. Multi-turn conversations
Зберігайте thread_id в сесії для продовження розмови:
```javascript
// Frontend: зберегти thread_id
sessionStorage.setItem('chat_thread_id', data.thread_id);

// Backend: використати існуючий thread
thread_id = request.json.get('thread_id')
if thread_id:
    # Додати message до існуючого thread
else:
    # Створити новий thread
```

---

## ✅ Checklist для запуску

- [ ] Видалити старі env vars: `OPENAI_AGENT_API_KEY`, `OPENAI_AGENT_API_URL`
- [ ] Додати `OPENAI_API_KEY` на Render
- [ ] Скопіювати `AGENT_SYSTEM_PROMPT.md` в Agent Builder Instructions
- [ ] Дочекатись deployment (~2-3 хв)
- [ ] Протестувати на https://vat-bot-1.onrender.com/chatbot/chat
- [ ] Перевірити логи в Render
- [ ] Встановити billing alert в OpenAI ($50/month)

---

**Все готово! Ваш AI асистент буде відповідати на питання німецькою про всі функції платформи.** 🎉

Якщо виникнуть проблеми - дивіться логи в Render, і я допоможу!
