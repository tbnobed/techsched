-- Add created_at column to schedule table if it doesn't exist
ALTER TABLE schedule ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Add location_id column to schedule table if it doesn't exist
ALTER TABLE schedule ADD COLUMN IF NOT EXISTS location_id INTEGER REFERENCES location(id);

-- Run VACUUM to optimize the database after schema changes
VACUUM ANALYZE;