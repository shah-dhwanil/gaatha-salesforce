-- 
-- depends: 20251231_05_xeay9

ALTER TABLE brand_categories
    ADD COLUMN parent_category_id INT REFERENCES brand_categories(id);