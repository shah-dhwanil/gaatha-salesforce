-- 
-- depends: 20251229_02_8wkFN

CREATE TABLE IF NOT EXISTS shop_categories(
    id SERIAL,
    name VARCHAR(32) NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_shop_categories PRIMARY KEY(id)
);

CREATE TRIGGER shop_categories_logs_set_updated_at
    BEFORE UPDATE ON shop_categories
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();