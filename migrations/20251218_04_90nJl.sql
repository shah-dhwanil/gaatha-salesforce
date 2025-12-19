-- 
-- depends: 20251218_03_jr2WV


ALTER TABLE salesforce.users
    ADD COLUMN IF NOT EXISTS company_id uuid NOT NULL REFERENCES salesforce.company(id);

CREATE INDEX IF NOT EXISTS idx_users_company_id
    ON salesforce.users(company_id);