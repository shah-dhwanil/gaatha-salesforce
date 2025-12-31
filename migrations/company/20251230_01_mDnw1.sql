-- 
-- depends: 20251229_03_bos8p

CREATE TABLE IF NOT EXISTS retailer(
    id uuid DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(255) NOT NULL,
    contact_person_name VARCHAR(255) NOT NULL,
    mobile_number VARCHAR(15) NOT NULL,
    email VARCHAR(255),
    gst_no VARCHAR(15) NOT NULL,
    pan_no VARCHAR(10) NOT NULL,
    license_no VARCHAR(255),
    address TEXT NOT NULL,
    category_id integer NOT NULL,
    pin_code VARCHAR(6) NOT NULL,
    map_link TEXT,
    documents JSONB,
    store_images JSONB,
    route_id integer NOT NULL,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT pk_retailer PRIMARY KEY (id),
    CONSTRAINT uniq_retailer_gst_no UNIQUE (gst_no),
    CONSTRAINT uniq_retailer_pan_no UNIQUE (pan_no),
    CONSTRAINT uniq_retailer_license_no UNIQUE (license_no),
    CONSTRAINT uniq_retailer_mobile_number UNIQUE (mobile_number),
    CONSTRAINT uniq_retailer_email UNIQUE (email),
    CONSTRAINT uniq_retailer_code UNIQUE (code),
    CONSTRAINT fk_retailer_shop_category FOREIGN KEY (category_id) REFERENCES shop_categories(id),
    CONSTRAINT fk_retailer_route FOREIGN KEY (route_id) REFERENCES routes(id)
);
CREATE SEQUENCE IF NOT EXISTS retailer_id_seq START 1 INCREMENT 1;
CREATE TRIGGER retailer_set_updated_at
    BEFORE UPDATE ON retailer
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();