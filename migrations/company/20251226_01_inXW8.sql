--
-- depends: 20251219_01_Fu3kI

CREATE TABLE IF NOT EXISTS routes(
    id SERIAL,
    name VARCHAR(32) NOT NULL,
    code VARCHAR(32) NOT NULL,
    area_id INTEGER NOT NULL,
    is_general boolean NOT NULL,
    is_modern boolean NOT NULL,
    is_horeca boolean NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_routes PRIMARY KEY (id),
    CONSTRAINT uniq_routes_code UNIQUE (code),
    CONSTRAINT fk_routes_area_id FOREIGN KEY (area_id) REFERENCES areas(id)
);

CREATE INDEX idx_routes_area_id ON routes (area_id) WHERE is_active = true;

CREATE TRIGGER routes_set_updated_at
    BEFORE UPDATE ON routes
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();
