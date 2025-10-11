-- SQL script to add user_id columns to tables for GDPR compliance
-- Run this on Render: psql $DATABASE_URL -f add_user_id_columns.sql

BEGIN;

-- Add user_id to companies table
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'companies' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE companies ADD COLUMN user_id INTEGER;
        ALTER TABLE companies ADD CONSTRAINT companies_user_id_fkey 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
        CREATE INDEX ix_companies_user_id ON companies(user_id);
        RAISE NOTICE 'Added user_id to companies table';
    ELSE
        RAISE NOTICE 'user_id already exists in companies table';
    END IF;
END $$;

-- Add user_id to counterparties table
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'counterparties' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE counterparties ADD COLUMN user_id INTEGER;
        ALTER TABLE counterparties ADD CONSTRAINT counterparties_user_id_fkey 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
        CREATE INDEX ix_counterparties_user_id ON counterparties(user_id);
        RAISE NOTICE 'Added user_id to counterparties table';
    ELSE
        RAISE NOTICE 'user_id already exists in counterparties table';
    END IF;
END $$;

-- Add user_id to verification_checks table
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'verification_checks' AND column_name = 'user_id'
    ) THEN
        -- First add as nullable
        ALTER TABLE verification_checks ADD COLUMN user_id INTEGER;
        
        -- Set default value for existing records (use first user's ID)
        UPDATE verification_checks 
        SET user_id = (SELECT id FROM users ORDER BY id LIMIT 1)
        WHERE user_id IS NULL;
        
        -- Make it NOT NULL
        ALTER TABLE verification_checks ALTER COLUMN user_id SET NOT NULL;
        
        -- Add foreign key constraint
        ALTER TABLE verification_checks ADD CONSTRAINT verification_checks_user_id_fkey 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
        
        -- Add index
        CREATE INDEX ix_verification_checks_user_id ON verification_checks(user_id);
        
        RAISE NOTICE 'Added user_id to verification_checks table';
    ELSE
        RAISE NOTICE 'user_id already exists in verification_checks table';
    END IF;
END $$;

-- Verify the changes
SELECT 
    'companies' as table_name,
    COUNT(*) as total_rows,
    COUNT(user_id) as rows_with_user_id
FROM companies
UNION ALL
SELECT 
    'counterparties' as table_name,
    COUNT(*) as total_rows,
    COUNT(user_id) as rows_with_user_id
FROM counterparties
UNION ALL
SELECT 
    'verification_checks' as table_name,
    COUNT(*) as total_rows,
    COUNT(user_id) as rows_with_user_id
FROM verification_checks;

COMMIT;

-- Success message
SELECT 'user_id columns successfully added to all tables!' as result;
