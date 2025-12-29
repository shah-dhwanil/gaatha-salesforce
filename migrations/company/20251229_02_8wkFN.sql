-- 
-- depends: 20251229_01_AjGGp

CREATE TABLE IF NOT EXISTS route_logs(
    id SERIAL,
    route_assignment_id INT NOT NULL,
    co_worker_id UUID,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME DEFAULT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_route_logs PRIMARY KEY (id),
    CONSTRAINT fk_route_logs_route_assignment_id FOREIGN KEY (route_assignment_id) REFERENCES route_assignments(id),
    CONSTRAINT fk_route_logs_co_worker_id FOREIGN KEY (co_worker_id) REFERENCES members(id),
    CONSTRAINT check_valid_time_range CHECK (end_time IS NULL OR end_time > start_time),
);

CREATE INDEX IF NOT EXISTS idx_route_logs_route_assignment_id ON route_logs(route_assignment_id);

CREATE TRIGGER route_logs_set_updated_at
    BEFORE UPDATE ON route_logs
    FOR EACH ROW
    EXECUTE FUNCTION trigger_set_updated_at();