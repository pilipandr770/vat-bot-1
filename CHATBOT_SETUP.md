# Claude (Anthropic) Chatbot Configuration

## Як це працює

Чатбот платформи побудований на Claude API (Anthropic). Використовується модель `claude-sonnet-4-6` безпосередньо через Python SDK — без проміжних сервісів.

---

## 1. Отримати API ключ

1. Зареєструватись на [console.anthropic.com](https://console.anthropic.com/)
2. Перейти в **Settings → API Keys**
3. Створити новий ключ
4. Зберегти безпечно — показується лише один раз

---

## 2. Налаштування для локальної розробки

Додати в `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
```

---

## 3. Налаштування для Render (Production)

```
Dashboard → Service → Environment → Add Environment Variable

Name:  ANTHROPIC_API_KEY
Value: sk-ant-api03-...
```

Render автоматично перезапустить сервіс після збереження.

---

## 4. Перевірка

```bash
# Запустити тестовий скрипт
python test_agent_api.py
```

Повинно вивести:
```
✅ SUCCESS! Claude API is working correctly.
```

---

## Компоненти чатботів

| Файл | Призначення |
|---|---|
| `services/chatbot_routes.py` | Чат для авторизованих користувачів (`/chatbot/api/chat/message`) |
| `services/chatbot_routes_sdk.py` | Альтернативна реалізація (резервна копія) |
| `services/sales_chatbot.py` | Публічний sales-чат на лендингу (`/api/sales-chat`) |
| `app/mailguard/nlp_reply.py` | AI-генерація відповідей на email |
| `app/pentesting/ai_analyzer.py` | AI-аналіз результатів сканування безпеки |
| `services/blog_generator.py` | Автоматична генерація SEO-статей |

Усі модулі використовують один і той самий `ANTHROPIC_API_KEY`.

---

## Cost Estimation

Claude Sonnet 4.6:
- Чат повідомлення: ~$0.003 – $0.01 за запит (залежить від довжини)
- Blog пост (~1000 слів): ~$0.02 – $0.05 за статтю
- Моніторинг використання: [console.anthropic.com](https://console.anthropic.com/)

---

## Security Notes

1. **Ніколи не комітити ключ** в Git репозиторій
2. Використовувати лише змінні оточення
3. Rate limiting вбудований в Anthropic SDK
4. При отриманні помилки 429 — SDK автоматично повідомляє про rate limit
