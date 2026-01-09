-- 
-- depends: 20251231_04_NbJWs

ALTER TABLE brand_categories
    ADD COLUMN parent_category_id INT REFERENCES brand_categories(id);