-- 
-- depends: 20251231_03_ChASK

CREATE TABLE brand_categories(
    id SERIAL,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(16) NOT NULL,
    for_general BOOLEAN DEFAULT FALSE,
    for_modern BOOLEAN DEFAULT FALSE,
    for_horeca BOOLEAN DEFAULT FALSE,
    logo JSONB,
    brand_id INT NOT NULL REFERENCES brand(id),
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_brand_categories PRIMARY KEY (id),
    CONSTRAINT uniq_brand_categories_code UNIQUE (code),
    CONSTRAINT fk_brand_categories_brand FOREIGN KEY (brand_id) REFERENCES brand(id)
);

CREATE TRIGGER brand_categories_set_updated_at
    BEFORE UPDATE ON brand_categories
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE brand_category_visibility(
    id SERIAL,
    brand_category_id INT,
    area_id INT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_brand_category_visibility PRIMARY KEY (id),
    CONSTRAINT fk_brand_category_visibility_brand_category FOREIGN KEY (brand_category_id) REFERENCES brand_categories(id),
    CONSTRAINT fk_brand_category_visibility_area FOREIGN KEY (area_id) REFERENCES areas(id)
);

CREATE UNIQUE INDEX uniq_brand_category_visibility_brand_category_area ON brand_category_visibility (brand_category_id, area_id) WHERE is_active = TRUE;
CREATE TRIGGER brand_category_visibility_set_updated_at
    BEFORE UPDATE ON brand_category_visibility
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE brand_category_margins(
    id SERIAL,
    name VARCHAR(255) NOT NULL,
    brand_category_id INT,
    area_id INT,
    margins JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_brand_category_margins PRIMARY KEY (id),
    CONSTRAINT fk_brand_category_margins_brand_category FOREIGN KEY (brand_category_id) REFERENCES brand_categories(id),
    CONSTRAINT fk_brand_category_margins_area FOREIGN KEY (area_id) REFERENCES areas(id),
    CONSTRAINT uniq_brand_category_margins UNIQUE (brand_category_id, area_id,is_active)
);

CREATE UNIQUE INDEX uniq_brand_category_margins_brand_category_area ON brand_category_margins (brand_category_id, area_id) WHERE is_active = TRUE;
CREATE TRIGGER brand_category_margins_set_updated_at
    BEFORE UPDATE ON brand_category_margins
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();