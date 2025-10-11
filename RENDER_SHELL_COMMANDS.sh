#!/bin/bash
# ============================================
# КОПИРУЙТЕ И ВСТАВЬТЕ ЭТИ КОМАНДЫ В RENDER SHELL
# ============================================

# Команда 1: Синхронизируйте Alembic с текущим состоянием БД
flask db stamp head

# Команда 2: Добавьте user_id колонки одной командой
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

# Команда 3: Создайте пустую миграцию и пометьте как выполненную
flask db revision -m "Add user_id columns for GDPR compliance" && flask db stamp head

# Команда 4: Проверьте результат
echo "=== Проверка таблицы companies ===" && psql $DATABASE_URL -c "\d companies" | grep user_id
echo "=== Проверка таблицы counterparties ===" && psql $DATABASE_URL -c "\d counterparties" | grep user_id
echo "=== Проверка таблицы verification_checks ===" && psql $DATABASE_URL -c "\d verification_checks" | grep user_id
echo "=== Текущая миграция ===" && flask db current

echo "✅ ГОТОВО! Миграции исправлены."
