-- 
-- depends: 20251226_02_DhGdE

ALTER TABLE members
    ADD COLUMN IF NOT EXISTS bank_details JSONB;