-- Submissions record the team's rank against the game's validation bots
-- (1 = best), computed from the validation run's total_points. NULL for
-- submissions made before this column existed.

ALTER TABLE submission ADD COLUMN IF NOT EXISTS ranking INTEGER;
