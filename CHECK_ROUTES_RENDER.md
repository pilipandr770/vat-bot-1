# 🚨 СРОЧНО: Команды для проверки routes на Render

## Скопируйте и выполните в Render Shell:

---

### 🔍 Команда 1: Проверка файлов

```bash
echo "=== Проверка legal директории ==="
ls -la legal/

echo ""
echo "=== Проверка templates ==="
ls -la templates/legal/

echo ""
echo "=== Проверка app.py ==="
grep "legal_bp" app.py
```

---

### 🔍 Команда 2: Проверка импорта

```bash
python3 << 'EOF'
import sys
import os
sys.path.insert(0, os.getcwd())

try:
    from legal.routes import legal_bp
    print("✅ legal_bp импортирован успешно")
    print(f"Имя: {legal_bp.name}")
    print(f"URL prefix: /legal")
except Exception as e:
    print(f"❌ Ошибка импорта: {e}")
    import traceback
    traceback.print_exc()
EOF
```

---

### 🔍 Команда 3: Проверка Flask routes

```bash
flask routes | grep legal
```

Ожидаемый результат:
```
legal.agb                    GET        /legal/agb
legal.datenschutz            GET        /legal/datenschutz
legal.delete_account         GET, POST  /legal/delete-account
legal.deletion_confirmed     GET        /legal/deletion-confirmed
legal.gdpr_request           GET, POST  /legal/gdpr-request
legal.impressum              GET        /legal/impressum
```

---

### 🔍 Команда 4: Проверка через curl

```bash
# Проверка impressum
curl -I http://localhost:$PORT/legal/impressum 2>/dev/null | head -1

# Проверка datenschutz
curl -I http://localhost:$PORT/legal/datenschutz 2>/dev/null | head -1

# Проверка agb
curl -I http://localhost:$PORT/legal/agb 2>/dev/null | head -1
```

Ожидаемый результат: `HTTP/1.1 200 OK`

---

## 🔥 ЕСЛИ ROUTES НЕ НАЙДЕНЫ:

### Решение: Перезапустите приложение

```bash
# Вариант 1: Через pkill
pkill -9 gunicorn
pkill -9 python

# Вариант 2: Через supervisor (если используется)
supervisorctl restart all
```

---

## 🎯 САМОЕ ВЕРОЯТНОЕ РЕШЕНИЕ:

### В Render Dashboard:

1. Откройте ваш сервис
2. Нажмите **"Manual Deploy"**
3. Выберите **"Clear build cache & deploy"**
4. Дождитесь завершения деплоя (~2-3 минуты)
5. Проверьте страницы снова

---

## 📋 После перезапуска проверьте:

```bash
# Проверка логов
tail -100 /var/log/render/*.log 2>/dev/null || echo "Логи не найдены"

# Проверка процессов
ps aux | grep python

# Проверка routes
flask routes | grep legal
```

---

## ✅ Если routes появились:

Откройте в браузере:
- `https://your-app.onrender.com/legal/impressum`
- `https://your-app.onrender.com/legal/datenschutz`
- `https://your-app.onrender.com/legal/agb`

---

## 🆘 Если всё ещё не работает:

Отправьте мне вывод этих команд:

```bash
echo "=== Git Commit ==="
git log -1 --oneline

echo ""
echo "=== Legal Files ==="
ls -la legal/

echo ""
echo "=== Flask Routes ==="
flask routes 2>&1

echo ""
echo "=== Python Path ==="
python3 -c "import sys; print('\n'.join(sys.path))"

echo ""
echo "=== Import Test ==="
python3 -c "from legal.routes import legal_bp; print('SUCCESS')" 2>&1
```

---

**90% вероятность:** Просто нужно сделать Manual Deploy на Render! 🔄
