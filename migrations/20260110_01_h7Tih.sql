-- 
-- depends: 20251225_01_ZaTWt

ALTER TABLE users
    ALTER COLUMN username DROP NOT NULL;

CREATE UNIQUE INDEX idx_users_contact_no_company ON users (contact_no, company_id) WHERE is_active = true;