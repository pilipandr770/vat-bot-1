# ⚡ ОКОНЧАТЕЛЬНОЕ РЕШЕНИЕ для Render (схема: vat_verification)

## 🎯 Вся необходимая информация

- **Схема БД:** `vat_verification`
- **Переменная в .env:** `DB_SCHEMA=vat_verification`
- **Config.py:** ✅ Уже настроен для работы со схемами
- **Миграция:** `361def0cfaed_initial_migration_with_all_models.py`

---

## 📋 ШАГ 1: Диагностика на Render

Скопируйте и выполните в Render Shell:

```bash
echo "=== 1. Проверка схемы vat_verification ==="
psql $DATABASE_URL -c "SELECT COUNT(*) as table_count FROM pg_tables WHERE schemaname = 'vat_verification';"

echo ""
echo "=== 2. Список таблиц в схеме ==="
psql $DATABASE_URL -c "SELECT tablename FROM pg_tables WHERE schemaname = 'vat_verification' ORDER BY tablename;"

echo ""
echo "=== 3. Проверка user_id в companies ==="
psql $DATABASE_URL -c "SELECT column_name FROM information_schema.columns WHERE table_schema = 'vat_verification' AND table_name = 'companies' AND column_name = 'user_id';" || echo "user_id отсутствует"

echo ""
echo "=== 4. Статус миграций Alembic ==="
psql $DATABASE_URL -c "SELECT version_num FROM vat_verification.alembic_version;" 2>/dev/null || echo "alembic_version не найдена"
```

---

## 🅰️ СЦЕНАРИЙ А: Схема пустая (таблиц нет)

```bash
# 1. Создайте схему
psql $DATABASE_URL -c "CREATE SCHEMA IF NOT EXISTS vat_verification;"

# 2. Примените миграции
flask db upgrade

# 3. Проверьте результат
psql $DATABASE_URL -c "SELECT tablename FROM pg_tables WHERE schemaname = 'vat_verification';"
```

**✅ ГОТОВО!** Таблицы созданы с user_id колонками (они уже в models.py).

---

## 🅱️ СЦЕНАРИЙ Б: Таблицы есть, но без user_id

### БЛОК 1: Синхронизация Alembic
```bash
flask db stamp head
```

### БЛОК 2: Добавление user_id (ВАЖНО: с указанием схемы!)
```bash
psql $DATABASE_URL << 'EOF'
-- Устанавливаем схему
SET search_path TO vat_verification, public;

BEGIN;

-- Добавляем user_id в companies
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'vat_verification' 
        AND table_name = 'companies' 
        AND column_name = 'user_id'
    ) THEN
        ALTER TABLE companies ADD COLUMN user_id INTEGER;
        ALTER TABLE companies ADD CONSTRAINT companies_user_id_fkey 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
        CREATE INDEX ix_companies_user_id ON companies(user_id);
    END IF;
END $$;

-- Добавляем user_id в counterparties
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'vat_verification' 
        AND table_name = 'counterparties' 
        AND column_name = 'user_id'
    ) THEN
        ALTER TABLE counterparties ADD COLUMN user_id INTEGER;
        ALTER TABLE counterparties ADD CONSTRAINT counterparties_user_id_fkey 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
        CREATE INDEX ix_counterparties_user_id ON counterparties(user_id);
    END IF;
END $$;

-- Добавляем user_id в verification_checks
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'vat_verification' 
        AND table_name = 'verification_checks' 
        AND column_name = 'user_id'
    ) THEN
        ALTER TABLE verification_checks ADD COLUMN user_id INTEGER;
        UPDATE verification_checks 
        SET user_id = (SELECT id FROM users ORDER BY id LIMIT 1) 
        WHERE user_id IS NULL;
        ALTER TABLE verification_checks ALTER COLUMN user_id SET NOT NULL;
        ALTER TABLE verification_checks ADD CONSTRAINT verification_checks_user_id_fkey 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        CREATE INDEX ix_verification_checks_user_id ON verification_checks(user_id);
    END IF;
END $$;

COMMIT;
EOF
```

### БЛОК 3: Финализация
```bash
flask db revision -m "Add user_id columns for GDPR compliance"
flask db stamp head
```

---

## 🅲 СЦЕНАРИЙ С: Нужно пересоздать всё с нуля

⚠️ **ВНИМАНИЕ: Это удалит все данные!**

```bash
# 1. Удалите схему
psql $DATABASE_URL -c "DROP SCHEMA IF EXISTS vat_verification CASCADE;"

# 2. Создайте заново
psql $DATABASE_URL -c "CREATE SCHEMA vat_verification;"

# 3. Примените миграции
flask db upgrade

# 4. Проверьте
psql $DATABASE_URL -c "\d vat_verification.companies" | grep user_id
```

---

## ✅ ПРОВЕРКА РЕЗУЛЬТАТА

```bash
# Проверьте наличие user_id колонок
echo "=== Companies ==="
psql $DATABASE_URL -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'vat_verification' AND table_name = 'companies' AND column_name = 'user_id';"

echo ""
echo "=== Counterparties ==="
psql $DATABASE_URL -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'vat_verification' AND table_name = 'counterparties' AND column_name = 'user_id';"

echo ""
echo "=== Verification Checks ==="
psql $DATABASE_URL -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'vat_verification' AND table_name = 'verification_checks' AND column_name = 'user_id';"

echo ""
echo "=== Миграции ==="
flask db current
```

Ожидаемый результат: В каждой таблице должна быть колонка `user_id` типа `integer`.

---

## 🔧 Настройка переменных на Render

В Render Dashboard → Settings → Environment:

```
DATABASE_URL=postgresql://user:pass@host/db
DB_SCHEMA=vat_verification
```

**✅ Config.py уже настроен для работы с этими переменными!**

---

## 🎉 После успешного выполнения

Ваше приложение будет:
- ✅ Работать со схемой `vat_verification`
- ✅ Иметь все таблицы с `user_id` колонками
- ✅ GDPR-compliant (функция удаления аккаунта работает)
- ✅ Все юридические страницы доступны

---

## 🆘 Если что-то пошло не так

### Ошибка: "schema vat_verification does not exist"
```bash
psql $DATABASE_URL -c "CREATE SCHEMA vat_verification;"
flask db upgrade
```

### Ошибка: "relation does not exist"
```bash
# Проверьте текущий search_path
psql $DATABASE_URL -c "SHOW search_path;"

# Установите правильный
psql $DATABASE_URL -c "SET search_path TO vat_verification, public;"
```

### Ошибка: "column already exists"
Это нормально! Колонка уже добавлена. Проверьте результат.

---

**Время выполнения:** 2-5 минут  
**Сложность:** ⭐⭐ (средняя)  
**Схема:** vat_verification  
**Статус:** ✅ Готово к использованию
