# 🚨 ИСПРАВЛЕННОЕ РЕШЕНИЕ - Таблицы не существуют

## Проблема
```
ERROR: relation "companies" does not exist
```

Таблицы еще не созданы в базе данных. Нужно сначала создать их.

---

## ✅ ПРАВИЛЬНОЕ РЕШЕНИЕ

### Шаг 1: Создайте таблицы через миграцию
```bash
flask db upgrade
```

**Это создаст все таблицы из миграций.**

---

### Шаг 2: Проверьте, что таблицы созданы
```bash
psql $DATABASE_URL -c "\dt"
```

Вы должны увидеть список таблиц: users, companies, counterparties, verification_checks и т.д.

---

### Шаг 3: Если таблицы созданы, но нет user_id колонок
```bash
# Проверьте структуру таблиц
psql $DATABASE_URL -c "\d companies"
psql $DATABASE_URL -c "\d counterparties"
psql $DATABASE_URL -c "\d verification_checks"
```

Если колонки `user_id` уже есть - **всё готово!** ✅

Если колонок нет - выполните:
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

## 🔍 Диагностика

### Проверьте текущий статус миграций
```bash
flask db current
```

Если ничего не показывает - миграции не применены.

### Посмотрите список всех миграций
```bash
flask db history
```

### Проверьте таблицы в БД
```bash
psql $DATABASE_URL -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public';"
```

---

## 🎯 ПОЛНОЕ РЕШЕНИЕ С НУЛЯ

Если база данных пустая, выполните по порядку:

```bash
# 1. Примените все миграции (создаст таблицы)
flask db upgrade

# 2. Проверьте статус
flask db current

# 3. Проверьте таблицы
psql $DATABASE_URL -c "\dt"

# 4. Проверьте структуру companies
psql $DATABASE_URL -c "\d companies"

# 5. Если user_id нет - добавьте (команды выше в Шаге 3)
```

---

## ⚠️ Возможные сценарии

### Сценарий А: База данных пустая
```bash
flask db upgrade
# Это создаст ВСЕ таблицы включая user_id колонки
# (если они есть в текущих моделях)
```

### Сценарий Б: Таблицы есть, но старые миграции не применены
```bash
flask db stamp head
# Пометить как применённые

flask db migrate -m "Add user_id columns"
# Создать новую миграцию

flask db upgrade
# Применить новую миграцию
```

### Сценарий В: Таблицы есть, миграции применены, но user_id нет
```bash
# Добавить вручную через SQL (Шаг 3 выше)
```

---

## 🆘 Что делать ПРЯМО СЕЙЧАС

Выполните эту команду, чтобы понять ситуацию:

```bash
echo "=== Проверка миграций ==="
flask db current
echo ""
echo "=== Список таблиц ==="
psql $DATABASE_URL -c "\dt"
echo ""
echo "=== Структура users ==="
psql $DATABASE_URL -c "\d users" 2>/dev/null || echo "Таблица users не существует"
echo ""
echo "=== Структура companies ==="
psql $DATABASE_URL -c "\d companies" 2>/dev/null || echo "Таблица companies не существует"
```

**Скопируйте и отправьте результат, и я скажу, что делать дальше!**

---

## 🎉 Скорее всего решение:

```bash
# Просто примените миграции!
flask db upgrade
```

Это создаст все таблицы. Если в текущих моделях (`crm/models.py`) уже есть `user_id`, то колонки создадутся автоматически!

---

**Создано:** 2025-10-11  
**Статус:** Исправлено для случая пустой БД
