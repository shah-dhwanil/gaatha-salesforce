-- 
-- depends: 20251231_02_fQtYg

CREATE TABLE brand(
    id SERIAL,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(16) NOT NULL,
    for_general BOOLEAN DEFAULT FALSE,
    for_modern BOOLEAN DEFAULT FALSE,
    for_horeca BOOLEAN DEFAULT FALSE,
    logo JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT pk_brand PRIMARY KEY (id),
    CONSTRAINT uniq_brand_code UNIQUE (code)
);
CREATE UNIQUE INDEX uniq_brand_name ON brand (name) WHERE is_active = TRUE AND is_deleted = FALSE;

CREATE TRIGGER brand_set_updated_at
    BEFORE UPDATE ON brand
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE brand_visibility(
    id SERIAL,
    brand_id INT NOT NULL REFERENCES brand(id),
    area_id INT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_brand_visibility PRIMARY KEY (id),
    CONSTRAINT fk_brand_visibility_brand FOREIGN KEY (brand_id) REFERENCES brand(id),
    CONSTRAINT fk_brand_visibility_area FOREIGN KEY (area_id) REFERENCES areas(id)
);

CREATE UNIQUE INDEX uniq_brand_visibility_brand_area ON brand_visibility (brand_id, area_id) WHERE is_active = TRUE;

CREATE TRIGGER brand_visibility_set_updated_at
    BEFORE UPDATE ON brand_visibility
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();


CREATE TABLE brand_margins(
    id SERIAL,
    name VARCHAR(255) NOT NULL,
    brand_id INT NOT NULL REFERENCES brand(id),
    area_id INT,
    margins JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_brand_margins PRIMARY KEY (id),
    CONSTRAINT fk_brand_margins_brand FOREIGN KEY (brand_id) REFERENCES brand(id),
    CONSTRAINT fk_brand_margins_area FOREIGN KEY (area_id) REFERENCES areas(id),
    CONSTRAINT uniq_brand_margins UNIQUE (brand_id, area_id,is_active)
);

CREATE UNIQUE INDEX uniq_brand_margins_brand_area ON brand_margins (brand_id, area_id) WHERE is_active = TRUE;

CREATE TRIGGER brand_margins_set_updated_at
    BEFORE UPDATE ON brand_margins
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();