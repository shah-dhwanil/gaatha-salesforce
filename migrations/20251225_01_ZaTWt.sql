-- 
-- depends: 20251218_04_90nJl

ALTER TABLE salesforce.users
    ADD COLUMN IF NOT EXISTS is_super_admin BOOLEAN DEFAULT FALSE;

ALTER TABLE salesforce.users
    ALTER COLUMN company_id DROP NOT NULL;