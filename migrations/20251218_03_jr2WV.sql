-- 
-- depends: 20251218_02_uWFbU

CREATE TABLE IF NOT EXISTS salesforce.company(
    id uuid DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    gst_no VARCHAR(15) NOT NULL,
    cin_no VARCHAR(21) NOT NULL,
    address TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    CONSTRAINT pk_company PRIMARY KEY (id)
);
CREATE UNIQUE INDEX uniq_company_gst_no ON salesforce.company (gst_no) WHERE is_active = true;
CREATE UNIQUE INDEX uniq_company_cin_no ON salesforce.company (cin_no) WHERE is_active = true;

CREATE TRIGGER company_set_updated_at
    BEFORE UPDATE ON salesforce.company
    FOR EACH ROW
    EXECUTE FUNCTION salesforce.trigger_set_updated_at();