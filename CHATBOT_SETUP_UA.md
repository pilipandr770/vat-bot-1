# Швидке Налаштування Чатбота — Claude (Anthropic)

## Що зроблено

Чатбот використовує **Claude API (Anthropic)** напряму:
- Модель `claude-sonnet-4-6`
- Передача контексту користувача
- Зберігання історії розмови (остані 20 повідомлень)
- Детальні логи для налагодження

---

## Що треба зробити ЗАРАЗ

### 1. Отримати API ключ

- Перейти на https://console.anthropic.com/settings/keys
- Створити новий ключ
- Скопіювати (показується раз!)

### 2. Додати на Render Dashboard

```
Dashboard → Service → Environment → Add Variable

ANTHROPIC_API_KEY = sk-ant-api03-ваш_ключ
```

**Видаліть старі змінні** (якщо є):
- `OPENAI_API_KEY`
- `OPENAI_AGENT_API_KEY`
- `OPENAI_AGENT_API_URL`

---

## Тестування

### Після deployment (~2-3 хв)

1. Відкрийте: https://vat-bot-1.onrender.com/chatbot/chat
2. Спробуйте:
   - "Wie starte ich eine Prüfung?"
   - "Was macht der OSINT-Scanner?"
   - "Wie ändere ich mein Abo?"

### Якщо працює
Агент дасть детальну відповідь німецькою з кроками, URLs, прикладами.

### Якщо НЕ працює
1. Перевірте логи в Render (Logs tab)
2. Запустіть `python test_agent_api.py` локально
3. Переконайтесь, що `ANTHROPIC_API_KEY` додано

---

## Документація

- **`CHATBOT_SETUP.md`** — повна інструкція налаштування
- **`CHATBOT_TROUBLESHOOTING.md`** — вирішення проблем
- **`AGENT_SYSTEM_PROMPT.md`** — системний промпт асистента

---

## Витрати

- ~$0.003–$0.01 за повідомлення
- Моніторинг: https://console.anthropic.com/

---

## Чеклист

- [ ] Додати `ANTHROPIC_API_KEY` на Render
- [ ] Зачекати deployment (~2-3 хв)
- [ ] Протестувати чатбот на production: /chatbot/chat
- [ ] Перевірити логи в Render
