-- 
-- depends: 20260101_01_g7kaG

CREATE TABLE IF NOT EXISTS products(
    id SERIAL,
    brand_id INT NOT NULL,
    brand_category_id INT NOT NULL,
    brand_subcategory_id INT,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(100) NOT NULL,
    description TEXT,
    barcode VARCHAR(100),
    hsn_code VARCHAR(8),
    gst_rate NUMERIC(5,2) NOT NULL,
    gst_category VARCHAR(100) NOT NULL,
    dimensions JSONB,
    compliance TEXT,
    measurement_details JSONB,
    packaging_type VARCHAR(100),
    packaging_details JSONB,
    images JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_products PRIMARY KEY (id),
    CONSTRAINT fk_products_brand FOREIGN KEY (brand_id) REFERENCES brand(id),
    CONSTRAINT fk_products_brand_category FOREIGN KEY (brand_category_id) REFERENCES brand_categories(id),
    CONSTRAINT fk_products_brand_subcategory FOREIGN KEY (brand_subcategory_id) REFERENCES brand_categories(id),
    CONSTRAINT chk_products_gst_rate CHECK (gst_rate >= 0 AND gst_rate <= 28)
);

CREATE UNIQUE INDEX uniq_products_brand_category_code ON products (code) WHERE is_active = TRUE;
CREATE INDEX idx_products_brand_id ON products (brand_id);
CREATE INDEX idx_products_brand_category_id ON products (brand_category_id);
CREATE INDEX idx_products_brand_subcategory_id ON products (brand_subcategory_id);

CREATE TRIGGER products_set_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE IF NOT EXISTS product_prices(
    id SERIAL,
    product_id INT NOT NULL,
    area_id INT,
    mrp NUMERIC(10,2) NOT NULL,
    margins JSONB,
    min_order_quantity JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_product_prices PRIMARY KEY (id),
    CONSTRAINT fk_product_prices_product FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT fk_product_prices_area FOREIGN KEY (area_id) REFERENCES areas(id),
    CONSTRAINT chk_product_prices_mrp CHECK (mrp >= 0)
);

CREATE UNIQUE INDEX uniq_product_prices_product_area ON product_prices (product_id, area_id) WHERE is_active = TRUE;

CREATE TRIGGER product_prices_set_updated_at
    BEFORE UPDATE ON product_prices
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();


CREATE TABLE IF NOT EXISTS product_visibility(
    id SERIAL,
    product_id INT NOT NULL,
    area_id INT NOT NULL,
    for_general BOOLEAN NOT NULL DEFAULT FALSE,
    for_modern BOOLEAN NOT NULL DEFAULT FALSE,
    for_horeca BOOLEAN NOT NULL DEFAULT FALSE,
    for_type_a BOOLEAN NOT NULL DEFAULT FALSE,
    for_type_b BOOLEAN NOT NULL DEFAULT FALSE,
    for_type_c BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_product_visibility PRIMARY KEY (id),
    CONSTRAINT fk_product_visibility_product FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT fk_product_visibility_area FOREIGN KEY (area_id) REFERENCES areas(id)
);
CREATE UNIQUE INDEX uniq_product_visibility_product_area ON product_visibility (product_id, area_id);
CREATE TRIGGER product_visibility_set_updated_at
    BEFORE UPDATE ON product_visibility
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();