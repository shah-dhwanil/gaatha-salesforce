-- 
-- depends: 20260105_01_uB1pb

CREATE OR REPLACE FUNCTION get_area_priority(p_area_type VARCHAR)
RETURNS INTEGER
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    RETURN CASE UPPER(p_area_type)
        WHEN 'NATION' THEN 1
        WHEN 'ZONE'   THEN 2
        WHEN 'REGION' THEN 3
        WHEN 'AREA'   THEN 4
        ELSE 5
    END;
END;
$$;
