# Инструкция по исправлению миграций на Render

## Проблема
База данных на Render уже содержит таблицы, но Alembic не знает о них.
Ошибка: `relation "users" already exists`

## Решение

### Шаг 1: Подключитесь к Render Shell
```bash
# В панели Render зайдите в Shell вашего сервиса
```

### Шаг 2: Пометьте текущую миграцию как выполненную (НЕ выполняя её)
```bash
cd ~/project/src
flask db stamp head
```

Это скажет Alembic, что текущая миграция уже применена к БД.

### Шаг 3: Создайте новую миграцию для user_id
```bash
flask db migrate -m "Add user_id to models for GDPR compliance"
```

### Шаг 4: Примените новую миграцию
```bash
flask db upgrade
```

### Шаг 5: Проверьте, что миграция прошла успешно
```bash
flask db current
```

## Альтернативное решение (если Шаг 2 не помог)

Если после `flask db stamp head` все еще возникают проблемы:

### Вариант A: Ручное добавление колонок через SQL
```bash
# Подключитесь к PostgreSQL
psql $DATABASE_URL

# Добавьте user_id в companies
ALTER TABLE companies ADD COLUMN IF NOT EXISTS user_id INTEGER;
ALTER TABLE companies ADD CONSTRAINT companies_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);
CREATE INDEX IF NOT EXISTS ix_companies_user_id ON companies(user_id);

# Добавьте user_id в counterparties
ALTER TABLE counterparties ADD COLUMN IF NOT EXISTS user_id INTEGER;
ALTER TABLE counterparties ADD CONSTRAINT counterparties_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);
CREATE INDEX IF NOT EXISTS ix_counterparties_user_id ON counterparties(user_id);

# Добавьте user_id в verification_checks
ALTER TABLE verification_checks ADD COLUMN IF NOT EXISTS user_id INTEGER NOT NULL DEFAULT 1;
ALTER TABLE verification_checks ADD CONSTRAINT verification_checks_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);
CREATE INDEX IF NOT EXISTS ix_verification_checks_user_id ON verification_checks(user_id);

# Выйдите из psql
\q
```

### Вариант B: Сброс миграций (ТОЛЬКО если нет важных данных)
```bash
# ВНИМАНИЕ: Это удалит таблицу alembic_version
psql $DATABASE_URL -c "DROP TABLE IF EXISTS alembic_version;"

# Затем пометьте текущую миграцию
flask db stamp head

# И создайте новую миграцию
flask db migrate -m "Add user_id to models for GDPR compliance"
flask db upgrade
```

## Проверка результата

После применения миграций проверьте структуру таблиц:
```bash
psql $DATABASE_URL -c "\d+ companies"
psql $DATABASE_URL -c "\d+ counterparties"
psql $DATABASE_URL -c "\d+ verification_checks"
```

Вы должны увидеть колонку `user_id` в каждой таблице.

## Если ничего не помогло

Создайте отдельный SQL-скрипт и выполните его:
```bash
cat > add_user_id.sql << 'EOF'
-- Add user_id to companies
ALTER TABLE companies ADD COLUMN IF NOT EXISTS user_id INTEGER;
ALTER TABLE companies ADD CONSTRAINT companies_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_companies_user_id ON companies(user_id);

-- Add user_id to counterparties  
ALTER TABLE counterparties ADD COLUMN IF NOT EXISTS user_id INTEGER;
ALTER TABLE counterparties ADD CONSTRAINT counterparties_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_counterparties_user_id ON counterparties(user_id);

-- Add user_id to verification_checks
ALTER TABLE verification_checks ADD COLUMN IF NOT EXISTS user_id INTEGER;
UPDATE verification_checks SET user_id = 1 WHERE user_id IS NULL;
ALTER TABLE verification_checks ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE verification_checks ADD CONSTRAINT verification_checks_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS ix_verification_checks_user_id ON verification_checks(user_id);
EOF

psql $DATABASE_URL -f add_user_id.sql
```

## Важно!

После успешного добавления колонок, **обязательно** создайте миграцию в Alembic:
```bash
# Создайте пустую миграцию
flask db revision -m "Mark user_id columns as added manually"

# Отредактируйте созданный файл миграции, оставив upgrade() и downgrade() пустыми
# Это нужно для синхронизации Alembic с реальным состоянием БД

# Примените пустую миграцию
flask db upgrade
```
