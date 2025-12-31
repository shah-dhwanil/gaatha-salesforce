-- 
-- depends: 20251230_01_mDnw1

CREATE TABLE IF NOT EXISTS distributor(
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
    pin_code VARCHAR(6) NOT NULL,
    map_link TEXT,
    documents JSONB,
    store_images JSONB,
    vehicle_3 integer NOT NULL,
    vehicle_4 integer NOT NULL,
    salesman_count integer NOT NULL,
    area_id integer NOT NULL,
    for_general BOOLEAN NOT NULL DEFAULT FALSE,
    for_modern BOOLEAN NOT NULL DEFAULT FALSE,
    for_horeca BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT pk_distributor PRIMARY KEY (id),
    CONSTRAINT uniq_distributor_gst_no UNIQUE (gst_no),
    CONSTRAINT uniq_distributor_pan_no UNIQUE (pan_no),
    CONSTRAINT uniq_distributor_license_no UNIQUE (license_no),
    CONSTRAINT uniq_distributor_mobile_number UNIQUE (mobile_number),
    CONSTRAINT uniq_distributor_email UNIQUE (email),
    CONSTRAINT uniq_distributor_code UNIQUE (code),
    CONSTRAINT fk_distributor_area_id FOREIGN KEY (area_id) REFERENCES areas(id)
);

CREATE SEQUENCE IF NOT EXISTS distributor_id_seq START 1 INCREMENT 1;

CREATE TRIGGER distributor_set_updated_at
    BEFORE UPDATE ON distributor
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();