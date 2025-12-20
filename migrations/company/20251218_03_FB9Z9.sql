-- 
-- depends: 20251218_02_LtWJU

CREATE TABLE IF NOT EXISTS areas(
    id SERIAL,
    name VARCHAR(64) NOT NULL,
    TYPE VARCHAR(32) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_areas PRIMARY KEY (id),
);

CREATE UNIQUE INDEX uniq_areas_name_type ON areas (name, type) WHERE is_active = true;

CREATE TRIGGER areas_set_updated_at
    BEFORE UPDATE ON areas
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();