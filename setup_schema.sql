-- Create dedicated schema for VAT Verification Platform
-- Run this in your existing PostgreSQL database on Render.com

-- Create schema
CREATE SCHEMA IF NOT EXISTS vat_verification;

-- Set search path to new schema
SET search_path TO vat_verification;

-- Grant permissions to your database user
GRANT ALL PRIVILEGES ON SCHEMA vat_verification TO ittoken_db_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA vat_verification TO ittoken_db_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA vat_verification TO ittoken_db_user;

-- Verify schema was created
SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'vat_verification';

-- After running this, you need to:
-- 1. Set DB_SCHEMA=vat_verification in Render environment variables
-- 2. Run Flask migrations: flask db upgrade
