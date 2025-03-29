-- Schema update script for Plex Technician Scheduler application
-- This script adds any missing columns required by the application

-- Add theme_preference column to user table if it doesn't exist
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS theme_preference VARCHAR(20) DEFAULT 'dark';

-- Add archived column to ticket table if it doesn't exist
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT false;

-- Check if columns were added
DO $$
BEGIN
    RAISE NOTICE 'Schema update completed.';
    RAISE NOTICE 'Checking if columns exist:';
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'user' AND column_name = 'theme_preference') THEN
        RAISE NOTICE 'user.theme_preference: EXISTS';
    ELSE
        RAISE NOTICE 'user.theme_preference: MISSING';
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'ticket' AND column_name = 'archived') THEN
        RAISE NOTICE 'ticket.archived: EXISTS';
    ELSE
        RAISE NOTICE 'ticket.archived: MISSING';
    END IF;

END $$;

-- Run VACUUM to optimize the database after schema changes
VACUUM ANALYZE;