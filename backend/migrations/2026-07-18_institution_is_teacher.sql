-- Institutions run by an individual teacher: the frontend swaps
-- league->classroom / team->student wording when this is set.
ALTER TABLE institution ADD COLUMN IF NOT EXISTS is_teacher BOOLEAN NOT NULL DEFAULT false;
