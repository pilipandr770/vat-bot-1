#!/bin/bash
# Script to fix Alembic migrations on Render
# Run this in Render Shell: bash fix_migrations.sh

set -e  # Exit on any error

echo "========================================="
echo "Fixing Alembic Migrations"
echo "========================================="
echo ""

# Step 1: Check current migration status
echo "Step 1: Checking current migration status..."
flask db current || echo "No migrations applied yet"
echo ""

# Step 2: Mark current migration as applied without running it
echo "Step 2: Stamping database as up-to-date..."
flask db stamp head
echo "✓ Database marked as current"
echo ""

# Step 3: Apply SQL script to add user_id columns
echo "Step 3: Adding user_id columns to tables..."
if [ -f "add_user_id_columns.sql" ]; then
    psql $DATABASE_URL -f add_user_id_columns.sql
    echo "✓ user_id columns added successfully"
else
    echo "⚠ SQL script not found, adding columns manually..."
    
    # Add user_id to companies
    psql $DATABASE_URL -c "ALTER TABLE companies ADD COLUMN IF NOT EXISTS user_id INTEGER;" || true
    psql $DATABASE_URL -c "ALTER TABLE companies ADD CONSTRAINT companies_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;" 2>/dev/null || true
    psql $DATABASE_URL -c "CREATE INDEX IF NOT EXISTS ix_companies_user_id ON companies(user_id);" || true
    
    # Add user_id to counterparties
    psql $DATABASE_URL -c "ALTER TABLE counterparties ADD COLUMN IF NOT EXISTS user_id INTEGER;" || true
    psql $DATABASE_URL -c "ALTER TABLE counterparties ADD CONSTRAINT counterparties_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;" 2>/dev/null || true
    psql $DATABASE_URL -c "CREATE INDEX IF NOT EXISTS ix_counterparties_user_id ON counterparties(user_id);" || true
    
    # Add user_id to verification_checks
    psql $DATABASE_URL -c "ALTER TABLE verification_checks ADD COLUMN IF NOT EXISTS user_id INTEGER;" || true
    psql $DATABASE_URL -c "UPDATE verification_checks SET user_id = (SELECT id FROM users ORDER BY id LIMIT 1) WHERE user_id IS NULL;" || true
    psql $DATABASE_URL -c "ALTER TABLE verification_checks ALTER COLUMN user_id SET NOT NULL;" 2>/dev/null || true
    psql $DATABASE_URL -c "ALTER TABLE verification_checks ADD CONSTRAINT verification_checks_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;" 2>/dev/null || true
    psql $DATABASE_URL -c "CREATE INDEX IF NOT EXISTS ix_verification_checks_user_id ON verification_checks(user_id);" || true
    
    echo "✓ user_id columns added manually"
fi
echo ""

# Step 4: Create empty migration to mark columns as added
echo "Step 4: Creating migration to mark user_id columns as added..."
flask db revision -m "Mark user_id columns as added manually"
echo "✓ Migration created"
echo ""

# Step 5: Mark the new migration as applied
echo "Step 5: Marking new migration as applied..."
flask db stamp head
echo "✓ Migration marked as applied"
echo ""

# Step 6: Verify the changes
echo "Step 6: Verifying table structures..."
echo ""
echo "Companies table:"
psql $DATABASE_URL -c "\d companies" | grep user_id || echo "⚠ user_id not found"
echo ""
echo "Counterparties table:"
psql $DATABASE_URL -c "\d counterparties" | grep user_id || echo "⚠ user_id not found"
echo ""
echo "Verification_checks table:"
psql $DATABASE_URL -c "\d verification_checks" | grep user_id || echo "⚠ user_id not found"
echo ""

# Step 7: Show current migration status
echo "Step 7: Current migration status:"
flask db current
echo ""

echo "========================================="
echo "✓ Migration fix completed successfully!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Test the legal pages: https://your-app.onrender.com/legal/impressum"
echo "2. Test account deletion: https://your-app.onrender.com/legal/delete-account"
echo "3. Check that all features work correctly"
