# 🚀 ШПАРГАЛКА: Команды для Render Shell

## 📍 НАЧНИТЕ С ЭТОГО ФАЙЛА!

Ваша схема: **vat_verification**

---

## 🔍 ШАГ 1: ДИАГНОСТИКА (обязательно!)

Вставьте это в Render Shell и посмотрите результат:

```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'vat_verification';"
```

**Результат:**
- `0` → Таблиц нет → Используйте **ВАРИАНТ A**
- `10+` → Таблицы есть → Используйте **ВАРИАНТ B**

---

## 🅰️ ВАРИАНТ A: Таблиц нет (count = 0)

### Одна команда:
```bash
psql $DATABASE_URL -c "CREATE SCHEMA IF NOT EXISTS vat_verification;" && flask db upgrade
```

**✅ ГОТОВО!** Все таблицы созданы с user_id.

---

## 🅱️ ВАРИАНТ B: Таблицы есть (count > 0)

### Команда 1: Синхронизация
```bash
flask db stamp head
```

### Команда 2: Добавление user_id
```bash
psql $DATABASE_URL << 'EOF'
SET search_path TO vat_verification, public;
BEGIN;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'vat_verification' AND table_name = 'companies' AND column_name = 'user_id') THEN ALTER TABLE companies ADD COLUMN user_id INTEGER; ALTER TABLE companies ADD CONSTRAINT companies_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL; CREATE INDEX ix_companies_user_id ON companies(user_id); END IF; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'vat_verification' AND table_name = 'counterparties' AND column_name = 'user_id') THEN ALTER TABLE counterparties ADD COLUMN user_id INTEGER; ALTER TABLE counterparties ADD CONSTRAINT counterparties_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL; CREATE INDEX ix_counterparties_user_id ON counterparties(user_id); END IF; END $$;
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'vat_verification' AND table_name = 'verification_checks' AND column_name = 'user_id') THEN ALTER TABLE verification_checks ADD COLUMN user_id INTEGER; UPDATE verification_checks SET user_id = (SELECT id FROM users ORDER BY id LIMIT 1) WHERE user_id IS NULL; ALTER TABLE verification_checks ALTER COLUMN user_id SET NOT NULL; ALTER TABLE verification_checks ADD CONSTRAINT verification_checks_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE; CREATE INDEX ix_verification_checks_user_id ON verification_checks(user_id); END IF; END $$;
COMMIT;
EOF
```

### Команда 3: Финализация
```bash
flask db revision -m "Add user_id" && flask db stamp head
```

---

## ✅ ПРОВЕРКА

```bash
psql $DATABASE_URL -c "SELECT column_name FROM information_schema.columns WHERE table_schema = 'vat_verification' AND table_name = 'companies' AND column_name = 'user_id';"
```

Если увидите `user_id` → **✅ УСПЕХ!**

---

## 📝 Переменные Render

В Settings → Environment добавьте:
```
DB_SCHEMA=vat_verification
```

---

## 🎉 Готово!

**Время:** 2 минуты  
**Подробности:** См. START_HERE_RENDER.md

