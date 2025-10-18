# OpenAI Agent Builder Configuration

## Agent API Integration

### Production (Render)
```bash
# У Render Dashboard → Environment Variables додати:

OPENAI_AGENT_API_URL=https://api.openai.com/v1/agents/run
OPENAI_AGENT_API_KEY=<your_openai_api_key>

# Або якщо Agent Builder має власний endpoint:
OPENAI_AGENT_API_URL=<custom_agent_endpoint_url>
OPENAI_AGENT_WORKFLOW_ID=wf_68f3ed065d5881909c95b20ad801090b07e400bf50570e4d
```

### Local Development (.env)
```bash
# Додати до .env файлу:

OPENAI_AGENT_API_URL=https://api.openai.com/v1/agents/run
OPENAI_AGENT_API_KEY=sk-proj-...your-api-key...
OPENAI_AGENT_WORKFLOW_ID=wf_68f3ed065d5881909c95b20ad801090b07e400bf50570e4d
```

---

## Agent Builder Deployment Options

### Option 1: OpenAI Platform API
Якщо ваш агент опублікований через OpenAI Platform:
- URL: `https://api.openai.com/v1/agents/<workflow_id>/run`
- Auth: Bearer token з OpenAI API key

### Option 2: Custom Endpoint
Якщо агент деплоїться окремо:
- Деплой workflow на serverless платформу (Vercel, AWS Lambda, Cloud Run)
- Створити HTTP endpoint що приймає `{"input_as_text": "..."}`
- Повертає `{"output_text": "..."}`

### Option 3: Direct Integration (рекомендовано)
Перенести логіку агента безпосередньо в Flask:
- Використати OpenAI SDK в Python
- Викликати модель з system prompt з вашого коду
- Уникнути додаткових HTTP запитів

---

## Integration Steps

### 1. Отримати API credentials
- Перейти на https://platform.openai.com/api-keys
- Створити новий API key
- Зберегти ключ безпечно

### 2. Налаштувати Agent Builder
- Якщо workflow вже створений - отримати його ID
- Або створити новий workflow і опублікувати

### 3. Додати змінні в Render
```
Dashboard → Service → Environment → Add Environment Variable
```

### 4. Перезапустити сервіс
Render автоматично перезапустить після додавання env vars.

---

## Testing Locally

```bash
# 1. Встановити dependencies (вже є в requirements.txt)
pip install httpx

# 2. Додати до .env
echo "OPENAI_AGENT_API_KEY=sk-proj-..." >> .env
echo "OPENAI_AGENT_API_URL=https://api.openai.com/v1/agents/run" >> .env

# 3. Запустити Flask
python app.py

# 4. Відкрити чат
http://localhost:5000/chatbot/chat
```

---

## API Request Format

**Ваш Flask → Agent Builder:**
```json
{
  "input_as_text": "Wie starte ich eine Prüfung?",
  "context": {
    "user_email": "user@example.com",
    "user_name": "Max Mustermann",
    "subscription_plan": "pro",
    "is_admin": false
  }
}
```

**Agent Builder → Ваш Flask:**
```json
{
  "output_text": "Im Dashboard links & in der Mitte die Felder ausfüllen...",
  "reasoning": "...",
  "tool_calls": []
}
```

---

## Security Notes

1. **Ніколи не комітити API keys** в Git
2. Використовувати змінні оточення
3. Обмежити rate limits на endpoint
4. Додати логування всіх запитів до агента
5. Встановити timeout (60 сек)

---

## Cost Estimation

Agent Builder з GPT-4:
- ~$0.01 - $0.03 за повідомлення
- Залежить від reasoning effort та tool calls
- Monitoring через OpenAI usage dashboard

---

## Alternative: Direct OpenAI Integration

Якщо не хочете використовувати Agent Builder endpoint, можна інтегрувати безпосередньо:

```python
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "<ваш system prompt>"},
        {"role": "user", "content": user_message}
    ]
)

answer = response.choices[0].message.content
```

Це дешевше та швидше, але без Agent Builder features (tools, workflows).
