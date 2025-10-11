# 🎯 ПРАВИЛЬНЫЕ КОМАНДЫ ДЛЯ RENDER (схема: vat_verification)

## ✅ ФИНАЛЬНОЕ РЕШЕНИЕ

Ваша схема: **vat_verification**

---

## 📋 БЛОК 1: Диагностика (выполните СНАЧАЛА)

```bash
echo "=== Проверка схемы vat_verification ==="
psql $DATABASE_URL -c "SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'vat_verification' ORDER BY tablename;"

echo ""
echo "=== Проверка таблицы users ==="
psql $DATABASE_URL -c "\d vat_verification.users" 2>/dev/null || echo "Таблица users не существует в схеме vat_verification"

echo ""
echo "=== Проверка таблицы companies ==="
psql $DATABASE_URL -c "\d vat_verification.companies" 2>/dev/null || echo "Таблица companies не существует в схеме vat_verification"

echo ""
echo "=== Статус миграций ==="
flask db current 2>/dev/null || echo "Миграции не инициализированы"
```

---

## 🅰️ Если таблиц НЕТ в схеме vat_verification

### ✅ БЛОК A1: Создайте схему и таблицы
```bash
# Создайте схему если её нет
psql $DATABASE_URL -c "CREATE SCHEMA IF NOT EXISTS vat_verification;"

# Установите search_path для Flask
export PGSCHEMA=vat_verification

# Примените миграции
flask db upgrade
```

---

## 🅱️ Если таблицы ЕСТЬ в схеме vat_verification

### ✅ БЛОК B1: Синхронизация Alembic
```bash
flask db stamp head
```

### ✅ БЛОК B2: Добавление user_id колонок (С УКАЗАНИЕМ СХЕМЫ!)
```bash
psql $DATABASE_URL << 'EOF'
SET search_path TO vat_verification, public;
BEGIN;

-- Companies table
ALTER TABLE companies ADD COLUMN IF NOT EXISTS user_id INTEGER;
ALTER TABLE companies ADD CONSTRAINT companies_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_companies_user_id ON companies(user_id);

-- Counterparties table
ALTER TABLE counterparties ADD COLUMN IF NOT EXISTS user_id INTEGER;
ALTER TABLE counterparties ADD CONSTRAINT counterparties_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_counterparties_user_id ON counterparties(user_id);

-- Verification checks table
ALTER TABLE verification_checks ADD COLUMN IF NOT EXISTS user_id INTEGER;
UPDATE verification_checks 
SET user_id = (SELECT id FROM users ORDER BY id LIMIT 1) 
WHERE user_id IS NULL;
ALTER TABLE verification_checks ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE verification_checks ADD CONSTRAINT verification_checks_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS ix_verification_checks_user_id ON verification_checks(user_id);

COMMIT;
EOF
```

### ✅ БЛОК B3: Финализация
```bash
flask db revision -m "Add user_id columns for GDPR compliance"
flask db stamp head
```

---

## ✓ ПРОВЕРКА РЕЗУЛЬТАТА

```bash
echo "=== Структура companies ==="
psql $DATABASE_URL -c "SET search_path TO vat_verification; \d companies" | grep user_id

echo ""
echo "=== Структура counterparties ==="
psql $DATABASE_URL -c "SET search_path TO vat_verification; \d counterparties" | grep user_id

echo ""
echo "=== Структура verification_checks ==="
psql $DATABASE_URL -c "SET search_path TO vat_verification; \d verification_checks" | grep user_id

echo ""
echo "=== Текущая миграция ==="
flask db current
```

---

## 🔧 Важно для config.py на Render

Убедитесь, что в вашем приложении установлена правильная схема:

```python
# В config.py или app.py должно быть:
import os
from sqlalchemy.engine.url import make_url

database_url = os.environ.get('DATABASE_URL')
if database_url:
    url = make_url(database_url)
    # Добавляем опцию для использования схемы vat_verification
    if 'postgresql' in database_url:
        database_url = f"{database_url}?options=-csearch_path=vat_verification"
```

Или добавьте в переменные окружения Render:
```
DATABASE_URL=postgresql://user:pass@host/db?options=-csearch_path=vat_verification
```

---

## 🎯 КРАТКАЯ ВЕРСИЯ (если таблицы уже есть)

```bash
# 1. Синхронизация
flask db stamp head

# 2. Добавление колонок со схемой
psql $DATABASE_URL << 'EOF'
SET search_path TO vat_verification, public;
BEGIN;
ALTER TABLE companies ADD COLUMN IF NOT EXISTS user_id INTEGER;
ALTER TABLE companies ADD CONSTRAINT companies_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_companies_user_id ON companies(user_id);
ALTER TABLE counterparties ADD COLUMN IF NOT EXISTS user_id INTEGER;
ALTER TABLE counterparties ADD CONSTRAINT counterparties_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_counterparties_user_id ON counterparties(user_id);
ALTER TABLE verification_checks ADD COLUMN IF NOT EXISTS user_id INTEGER;
UPDATE verification_checks SET user_id = (SELECT id FROM users ORDER BY id LIMIT 1) WHERE user_id IS NULL;
ALTER TABLE verification_checks ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE verification_checks ADD CONSTRAINT verification_checks_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS ix_verification_checks_user_id ON verification_checks(user_id);
COMMIT;
EOF

# 3. Финализация
flask db revision -m "Add user_id columns"
flask db stamp head
```

---

## 🎉 Готово!

После выполнения команд ваше приложение будет работать со схемой `vat_verification` и иметь все необходимые колонки для GDPR-compliance.

**Время:** 2-3 минуты  
**Схема:** vat_verification  
**Статус:** ✅ Готово к использованию
