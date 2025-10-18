# 🔧 Налаштування Agent Builder API

## Проблема
Отримуємо помилку 500 при відправці повідомлень до чатбота. Це може бути через:
1. Неправильний URL endpoint
2. Неправильний формат запиту
3. Неправильний API ключ

## 📋 Крок 1: Знайдіть правильний endpoint

### Варіант А: OpenAI Platform API
Якщо ви створили агента через OpenAI Platform (Assistants API):

**URL**: `https://api.openai.com/v1/assistants/{assistant_id}/run`

**Потрібні змінні**:
```
OPENAI_API_KEY=sk-proj-ваш_ключ
OPENAI_ASSISTANT_ID=asst_ваш_id_асистента
```

### Варіант Б: Agent Builder Workflow
Якщо ви використовуєте Agent Builder з workflow ID `wf_68f3ed065d5881909c95b20ad801090b07e400bf50570e4d`:

**Можливі endpoints**:
- `https://api.openai.com/v1/workflows/{workflow_id}/run`
- `https://api.openai.com/v1/agents/workflows/{workflow_id}/execute`
- Або кастомний endpoint від OpenAI

**Де знайти правильний URL**:
1. Відкрийте OpenAI Agent Builder
2. Знайдіть ваш workflow
3. Шукайте секцію "API Access" або "Deployment"
4. Скопіюйте endpoint URL

### Варіант В: Assistants API v2
Нова версія Assistants API:

**URL**: `https://api.openai.com/v1/threads/runs`

**Метод**: POST з створенням thread спочатку

## 🧪 Крок 2: Протестуйте локально

### Тест 1: HTTP запит
```powershell
python test_agent_api.py
```

Цей скрипт спробує відправити запит до вашого Agent API і покаже детальну відповідь.

### Тест 2: OpenAI SDK
Якщо Варіант А працює, можете використати альтернативну реалізацію:

1. В `app.py` замініть:
```python
# Старий
from services.chatbot_routes import chatbot_bp

# Новий (SDK version)
from services.chatbot_routes_sdk import chatbot_sdk_bp as chatbot_bp
```

2. Додайте на Render:
```
OPENAI_API_KEY=sk-proj-ваш_ключ
OPENAI_ASSISTANT_ID=asst_ваш_id
```

## 🔍 Крок 3: Перегляньте логи на Render

Після deployment з логуванням ви побачите в логах:
```
[CHATBOT] Calling Agent API: https://...
[CHATBOT] User message: Wie starte ich eine Prüfung?
[CHATBOT] Response status: 404 (або інший код)
[CHATBOT] Response body: {"error": "..."}
```

Це допоможе зрозуміти, що саме не працює.

## ✅ Крок 4: Виправте конфігурацію

Коли знайдете правильний endpoint:

1. **Оновіть на Render**:
   - Dashboard → Environment
   - Змініть `OPENAI_AGENT_API_URL` на правильний
   - Збережіть

2. **Або використайте SDK версію**:
   - Якщо ваш агент - це Assistants API
   - Використайте `chatbot_routes_sdk.py`
   - Потрібен тільки `OPENAI_API_KEY` та `OPENAI_ASSISTANT_ID`

## 📚 Документація OpenAI

- **Assistants API**: https://platform.openai.com/docs/assistants/overview
- **API Reference**: https://platform.openai.com/docs/api-reference/assistants
- **Agent Builder Docs**: (перевірте в OpenAI Platform)

## 🆘 Що робити далі?

1. Запустіть `python test_agent_api.py` локально
2. Подивіться на помилку в консолі
3. Знайдіть правильний endpoint в документації OpenAI
4. Оновіть змінні середовища на Render
5. Або перейдіть на SDK версію з `chatbot_routes_sdk.py`

---

**Потрібна допомога?**
Скопіюйте вивід з `test_agent_api.py` або логи з Render, і я допоможу налаштувати правильний endpoint.
