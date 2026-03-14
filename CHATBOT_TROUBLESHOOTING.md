# Troubleshooting — Claude Chatbot

## Chatbot не відповідає / помилка 500

### Крок 1: Перевірте ANTHROPIC_API_KEY

**Production (Render):**
```
Dashboard → Service → Environment
→ Перевірте наявність ANTHROPIC_API_KEY
```

**Локально:**
```bash
# .env файл повинен містити:
ANTHROPIC_API_KEY=sk-ant-api03-...
```

---

### Крок 2: Запустіть тестовий скрипт

```bash
python test_agent_api.py
```

**Можливі результати:**

| Помилка | Причина | Рішення |
|---|---|---|
| `ANTHROPIC_API_KEY not set` | Немає ключа в `.env` | Додати ключ |
| `AuthenticationError` | Невалідний ключ | Перевірити ключ на console.anthropic.com |
| `RateLimitError` | Перевищено ліміт запитів | Зачекати або підвищити план |
| `APIConnectionError` | Мережева проблема | Перевірити з'єднання |
| `✅ SUCCESS` | Все працює | — |

---

### Крок 3: Перегляньте логи Render

Render Dashboard → Service → **Logs**

Що шукати:
```
ERROR: ANTHROPIC_API_KEY not configured
ERROR: Claude reply generation error: ...
ERROR: Authentication error
```

---

### Крок 4: Перевірте модель

Поточна модель: `claude-sonnet-4-6`

Якщо модель застаріла, оновіть константу `CLAUDE_MODEL` у файлах:
- `services/chatbot_routes.py`
- `services/sales_chatbot.py`
- `app/mailguard/nlp_reply.py`
- `app/pentesting/ai_analyzer.py`
- `services/blog_generator.py`

Актуальні моделі: [docs.anthropic.com/en/docs/about-claude/models](https://docs.anthropic.com/en/docs/about-claude/models)

---

## Документація Anthropic

- **Messages API**: https://docs.anthropic.com/en/api/messages
- **Python SDK**: https://github.com/anthropics/anthropic-sdk-python
- **Моделі**: https://docs.anthropic.com/en/docs/about-claude/models
- **Console**: https://console.anthropic.com/

---

## Ключові точки використання Claude

1. `/chatbot/api/chat/message` — чат для авторизованих користувачів
2. `/api/sales-chat` — публічний sales assistant (Alex)
3. MailGuard → AI-генерація відповідей на email
4. Pentesting → AI-аналіз результатів сканування
5. Blog → щоденна SEO-автогенерація статей
