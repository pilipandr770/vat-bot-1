# 🚀 Швидке Налаштування Чатбота - Українською

## ✅ Що зроблено

Ваш чатбот **переписано** під правильну інтеграцію з Agent Builder:
- ✅ Використовує **OpenAI Agents SDK** (не HTTP API)
- ✅ Thread-based розмови (як ChatGPT)
- ✅ Ваш workflow ID вже в коді
- ✅ Передача контексту користувача німецькою
- ✅ Детальні логи для налагодження

---

## 🔧 Що треба зробити ЗАРАЗ

### 1. На Render Dashboard

**Видаліть старі змінні** (якщо є):
- ❌ `OPENAI_AGENT_API_KEY`
- ❌ `OPENAI_AGENT_API_URL`

**Додайте ОДНУ нову змінну**:
```
OPENAI_API_KEY = sk-proj-ваш_ключ_з_openai
```

**Де взяти ключ?**
- https://platform.openai.com/api-keys
- Create new secret key
- Скопіюйте (показується раз!)

### 2. В Agent Builder (OpenAI Platform)

1. Відкрийте ваш агент в Agent Builder
2. Знайдіть секцію **"Instructions"** або **"System Prompt"**
3. Відкрийте файл **`AGENT_SYSTEM_PROMPT.md`** (в проєкті)
4. **Скопіюйте весь текст** з файлу в Instructions
5. Збережіть

**Що дає цей промпт?**
- Агент знає всі функції платформи (Dashboard, VAT перевірки, OSINT, ціни)
- Відповідає німецькою з конкретними інструкціями
- Підказує URLs (`/verify`, `/osint/scan`, etc.)
- Використовує контекст користувача

---

## 🧪 Тестування

### Після deployment (~2-3 хв)

1. Відкрийте: https://vat-bot-1.onrender.com/chatbot/chat
2. Спробуйте:
   - "Wie starte ich eine Prüfung?"
   - "Was macht der OSINT-Scanner?"
   - "Wie ändere ich mein Abo?"

### Якщо працює ✅
Агент дасть **детальну відповідь німецькою** з кроками, URLs, прикладами.

### Якщо НЕ працює ❌
1. Перевірте логи в Render (будуть детальні помилки)
2. Переконайтесь, що `OPENAI_API_KEY` додано
3. Перевірте, що System Prompt скопійовано в Agent Builder
4. Зачекайте 5 хвилин (синхронізація OpenAI)

---

## 📚 Документація

- **`AGENT_SDK_SETUP_FINAL.md`** - повна інструкція англійською (детально все)
- **`AGENT_SYSTEM_PROMPT.md`** - промпт для агента (скопіювати в Agent Builder)
- **Логи Render** - покажуть точну помилку якщо щось не так

---

## 💰 Витрати

- ~$0.01-$0.03 за повідомлення
- ~$1-3 за 100 повідомлень
- Встановіть billing limit $50/місяць для безпеки

---

## ✅ Чеклист

- [ ] Видалити `OPENAI_AGENT_API_KEY` та `OPENAI_AGENT_API_URL` з Render
- [ ] Додати `OPENAI_API_KEY` на Render
- [ ] Скопіювати `AGENT_SYSTEM_PROMPT.md` в Agent Builder Instructions
- [ ] Зачекати deployment (~2-3 хв)
- [ ] Протестувати чатбот на production
- [ ] Перевірити логи в Render

---

**Все! Ваш AI асистент готовий підказувати користувачам німецькою про всі функції платформи.** 🎉

Якщо щось не працює - скопіюйте логи з Render, і я допоможу!
