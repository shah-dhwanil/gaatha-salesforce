-- 
-- depends: 20251226_01_inXW8

CREATE TABLE IF NOT EXISTS route_assignment(
    id SERIAL,
    route_id INTEGER NOT NULL,
    user_id UUID NOT NULL,
    from_date DATE NOT NULL,
    to_date DATE,
    day INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_route_assignment PRIMARY KEY (id),
    CONSTRAINT fk_route_assignment_route_id FOREIGN KEY (route_id) REFERENCES routes(id),
    CONSTRAINT fk_route_assignment_user_id FOREIGN KEY (user_id) REFERENCES members(id),
    CONSTRAINT check_valid_date_range CHECK (to_date IS NULL OR to_date >= from_date),
    CONSTRAINT check_day_valid CHECK (day >= 0 AND day <= 6)
);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_route_user_active ON route_assignment (route_id, user_id) WHERE is_active = true;