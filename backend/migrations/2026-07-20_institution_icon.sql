-- Emoji or image URL shown next to the name on the public competition
-- picker (student login page). Only meaningful for non-teacher accounts.
ALTER TABLE institution ADD COLUMN IF NOT EXISTS icon TEXT;
