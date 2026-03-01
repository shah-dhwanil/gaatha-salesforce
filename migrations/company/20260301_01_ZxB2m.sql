-- Remove NOT NULL constraint from gst_no and pan_no in distributors and retailers
-- depends: 20260120_01_Y0kx4

-- Alter retailer table
ALTER TABLE retailer
ALTER COLUMN gst_no DROP NOT NULL,
ALTER COLUMN pan_no DROP NOT NULL;

-- Alter distributor table
ALTER TABLE distributor
ALTER COLUMN gst_no DROP NOT NULL,
ALTER COLUMN pan_no DROP NOT NULL;

