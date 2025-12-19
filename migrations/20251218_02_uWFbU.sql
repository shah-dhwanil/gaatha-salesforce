-- 
-- depends: 20251218_01_x8Zu7

CREATE TABLE IF NOT EXISTS salesforce.users(
    id UUID DEFAULT gen_random_uuid(),
    username varchar(32) NOT NULL,
    name varchar(64) NOT NULL,
    contact_no varchar(15) NOT NULL,
    role varchar(16) NOT NULL,
    is_active boolean DEFAULT true,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    CONSTRAINT pk_users PRIMARY KEY(id),
    CONSTRAINT uniq_users_username UNIQUE(username)
);

CREATE TRIGGER users_set_updated_at
    BEFORE UPDATE ON salesforce.users
    FOR EACH ROW
    EXECUTE FUNCTION salesforce.trigger_set_updated_at();