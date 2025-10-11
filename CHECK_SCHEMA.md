# 🔍 ДИАГНОСТИКА: Проверка схем PostgreSQL

## Проблема
В базе данных может быть несколько схем (schemas), и таблицы находятся в конкретной схеме, а не в public.

---

## ✅ Шаг 1: Проверьте схемы в БД

```bash
psql $DATABASE_URL -c "SELECT schema_name FROM information_schema.schemata;"
```

---

## ✅ Шаг 2: Проверьте таблицы во ВСЕХ схемах

```bash
psql $DATABASE_URL -c "SELECT schemaname, tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema') ORDER BY schemaname, tablename;"
```

---

## ✅ Шаг 3: Найдите таблицу users

```bash
psql $DATABASE_URL -c "SELECT schemaname, tablename FROM pg_tables WHERE tablename = 'users';"
```

Это покажет, в какой схеме находится таблица users.

---

## ✅ Шаг 4: Проверьте текущий search_path

```bash
psql $DATABASE_URL -c "SHOW search_path;"
```

---

## ✅ Шаг 5: Посмотрите все таблицы в текущей схеме

```bash
psql $DATABASE_URL -c "\dt"
```

Или с указанием схемы:
```bash
psql $DATABASE_URL -c "\dt public.*"
psql $DATABASE_URL -c "\dt your_schema_name.*"
```

---

## 🎯 ПОЛНАЯ ДИАГНОСТИКА (скопируйте это)

```bash
echo "=== 1. Список схем ==="
psql $DATABASE_URL -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema');"

echo ""
echo "=== 2. Текущий search_path ==="
psql $DATABASE_URL -c "SHOW search_path;"

echo ""
echo "=== 3. Таблицы во всех схемах ==="
psql $DATABASE_URL -c "SELECT schemaname, tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema') ORDER BY schemaname;"

echo ""
echo "=== 4. Где находится таблица users ==="
psql $DATABASE_URL -c "SELECT schemaname FROM pg_tables WHERE tablename = 'users';"

echo ""
echo "=== 5. Где находится таблица companies ==="
psql $DATABASE_URL -c "SELECT schemaname FROM pg_tables WHERE tablename = 'companies';"

echo ""
echo "=== 6. Миграции Alembic ==="
psql $DATABASE_URL -c "SELECT version_num FROM alembic_version;" 2>/dev/null || echo "Таблица alembic_version не найдена"
```

---

## 📤 ОТПРАВЬТЕ МНЕ РЕЗУЛЬТАТ

Скопируйте весь вывод и отправьте мне. Я скажу, какие команды нужно выполнить с учетом вашей схемы!

---

## 🔧 Возможные решения

### Если таблицы в схеме "public":
```bash
flask db upgrade
```

### Если таблицы в другой схеме (например "myschema"):
```bash
# Установите search_path
export PGSCHEMA=myschema

# Или укажите схему в DATABASE_URL
# postgresql://user:pass@host/db?options=-csearch_path=myschema

# Или выполните миграции с указанием схемы
psql $DATABASE_URL -c "SET search_path TO myschema; CREATE TABLE IF NOT EXISTS ..."
```

---

## ⚡ Быстрая проверка

```bash
# Проверьте, есть ли таблицы в public
psql $DATABASE_URL -c "SELECT COUNT(*) as tables_in_public FROM pg_tables WHERE schemaname = 'public';"

# Проверьте общее количество таблиц
psql $DATABASE_URL -c "SELECT schemaname, COUNT(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema') GROUP BY schemaname;"
```

---

**ВЫПОЛНИТЕ ДИАГНОСТИКУ И ОТПРАВЬТЕ РЕЗУЛЬТАТ!** 🔍
