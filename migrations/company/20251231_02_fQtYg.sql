-- 
-- depends: 20251231_01_MIBDw

CREATE TABLE IF NOT EXISTS distributor_routes(
    distributor_id uuid NOT NULL REFERENCES distributor(id),
    route_id integer NOT NULL REFERENCES routes(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    CONSTRAINT pk_distributor_routes PRIMARY KEY (distributor_id, route_id,is_active),
    CONSTRAINT fk_distributor_routes_distributor FOREIGN KEY (distributor_id) REFERENCES distributor(id),
    CONSTRAINT fk_distributor_routes_route FOREIGN KEY (route_id) REFERENCES routes(id)
);
CREATE INDEX IF NOT EXISTS idx_distributor_routes_distributor_id ON distributor_routes(distributor_id);
CREATE INDEX IF NOT EXISTS idx_distributor_routes_route_id ON distributor_routes(route_id);

CREATE TRIGGER distributor_routes_set_updated_at
    BEFORE UPDATE ON distributor_routes
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();