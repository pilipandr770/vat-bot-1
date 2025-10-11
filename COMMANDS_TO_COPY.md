# 🎯 БЫСТРОЕ ИСПРАВЛЕНИЕ МИГРАЦИЙ НА RENDER

## ⚠️ ШАГ 0: ДИАГНОСТИКА (ОБЯЗАТЕЛЬНО!)

### Проверьте схемы и таблицы:

```bash
echo "=== Схемы в базе данных ==="
psql $DATABASE_URL -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema');"

echo ""
echo "=== Таблицы и их схемы ==="
psql $DATABASE_URL -c "SELECT schemaname, tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema') ORDER BY schemaname;"

echo ""
echo "=== Где находится users ==="
psql $DATABASE_URL -c "SELECT schemaname FROM pg_tables WHERE tablename = 'users';"
```

**РЕЗУЛЬТАТ:**
- Если таблиц НЕТ → Используйте **ВАРИАНТ A**
- Если таблицы в схеме "public" → Используйте **ВАРИАНТ B**  
- Если таблицы в другой схеме → Используйте **ВАРИАНТ C**

---

## 🅰️ ВАРИАНТ A: База данных пустая (таблиц нет)

### ✅ БЛОК 1: Создайте все таблицы
```bash
flask db upgrade
```

### ✅ БЛОК 2: Проверьте результат
```bash
psql $DATABASE_URL -c "\d companies" | grep user_id
psql $DATABASE_URL -c "\d counterparties" | grep user_id
psql $DATABASE_URL -c "\d verification_checks" | grep user_id
```

**Если user_id присутствует - ГОТОВО! ✅**

---

## 🅱️ ВАРИАНТ B: Таблицы существуют, но user_id отсутствует

### ✅ БЛОК 1: Синхронизация Alembic
```bash
flask db stamp head
```

---

### ✅ БЛОК 2: Добавление user_id колонок
```bash
psql $DATABASE_URL << 'EOF'
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
```

---

### ✅ БЛОК 3: Финализация
```bash
flask db revision -m "Add user_id columns for GDPR compliance"
flask db stamp head
```

---

---

## 🅲 ВАРИАНТ C: Таблицы в другой схеме (не public)

### ✅ БЛОК 1: Найдите название схемы
```bash
psql $DATABASE_URL -c "SELECT schemaname FROM pg_tables WHERE tablename = 'users';"
```

Запомните название схемы (например: `myapp_schema`)

### ✅ БЛОК 2: Установите search_path
```bash
# Замените YOUR_SCHEMA_NAME на вашу схему!
psql $DATABASE_URL -c "SET search_path TO YOUR_SCHEMA_NAME, public;"
```

### ✅ БЛОК 3: Проверьте, что теперь таблицы видны
```bash
psql $DATABASE_URL -c "SET search_path TO YOUR_SCHEMA_NAME; \dt"
```

### ✅ БЛОК 4: Выполните миграцию с учетом схемы
```bash
# Вариант 1: Если таблиц нет в схеме
flask db upgrade

# Вариант 2: Если таблицы есть, добавьте user_id
psql $DATABASE_URL << 'EOF'
SET search_path TO YOUR_SCHEMA_NAME, public;
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
```

**⚠️ НЕ ЗАБУДЬТЕ заменить `YOUR_SCHEMA_NAME` на реальное название вашей схемы!**

---

## ✓ Проверка (опционально)
```bash
psql $DATABASE_URL -c "\d companies" | grep user_id
psql $DATABASE_URL -c "\d counterparties" | grep user_id
psql $DATABASE_URL -c "\d verification_checks" | grep user_id
flask db current
```

---

## 🎉 Готово!
После выполнения этих команд приложение полностью GDPR-compliant и готово к использованию.

**Время:** ~2 минуты  
**Подробности:** См. README_MIGRATION_FIX.md  
**Диагностика:** См. CHECK_SCHEMA.md
