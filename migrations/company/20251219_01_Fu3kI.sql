-- 
-- depends: 20251218_04_SaAuJ
CREATE TABLE IF NOT EXISTS members(
    id uuid REFERENCES salesforce.users(id),
    role VARCHAR(32) REFERENCES roles(name),
    area_id INT REFERENCES areas(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_company_users PRIMARY KEY (id,is_active)
);

CREATE INDEX IF NOT EXISTS idx_members_area_id ON members(area_id);
CREATE INDEX IF NOT EXISTS idx_members_role ON members(role);


CREATE TRIGGER members_set_updated_at
    BEFORE UPDATE ON members
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();