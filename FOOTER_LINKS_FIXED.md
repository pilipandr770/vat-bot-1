# ✅ ИСПРАВЛЕНО: Ссылки footer на landing page

## 🐛 Проблема

На landing page (главной странице) ссылки в footer вели на `#` (пустой якорь), поэтому при клике страница прокручивалась вверх, но не переходила на юридические страницы.

---

## ✅ Что было исправлено

### До (неправильно):
```html
<a href="#" class="text-white me-3">AGB</a>
<a href="#" class="text-white me-3">Datenschutz</a>
<a href="#" class="text-white">Impressum</a>
```

### После (правильно):
```html
<a href="{{ url_for('legal.agb') }}" class="text-white me-3">AGB</a>
<a href="{{ url_for('legal.datenschutz') }}" class="text-white me-3">Datenschutz</a>
<a href="{{ url_for('legal.impressum') }}" class="text-white">Impressum</a>
```

---

## 📁 Изменённый файл

- `templates/landing.html` - строки 362-364

---

## ✅ Результат

Теперь на landing page (https://your-app.onrender.com/) все ссылки в footer работают правильно:

- ✅ **AGB** → `/legal/agb`
- ✅ **Datenschutz** → `/legal/datenschutz`
- ✅ **Impressum** → `/legal/impressum`

---

## 🚀 Деплой на Render

Изменения уже закоммичены и отправлены на GitHub:

```bash
git commit: "fix: replace placeholder links in landing page footer with actual legal routes"
```

Render автоматически задеплоит изменения через 1-2 минуты.

---

## 🔍 Проверка

После деплоя:

1. Откройте главную страницу: `https://your-app.onrender.com/`
2. Прокрутите вниз до footer
3. Кликните на **Impressum** → должно открыть `/legal/impressum`
4. Кликните на **Datenschutz** → должно открыть `/legal/datenschutz`
5. Кликните на **AGB** → должно открыть `/legal/agb`

---

## 📝 Дополнительно

Также добавлена USt-IdNr в footer landing page:
```html
<p>&copy; 2025 VAT Verifizierung. Alle Rechte vorbehalten. | USt-IdNr: DE456902445</p>
```

---

## ✅ Статус

**Исправлено:** 2025-10-11  
**Коммит:** 5b8ea2f  
**Файл:** templates/landing.html  
**Статус:** ✅ Готово
