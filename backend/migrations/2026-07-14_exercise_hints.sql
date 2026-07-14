-- Hints move out of problem_markdown into a structured list (one Markdown
-- string per hint) so the problem text stays brief. Backfill then drop the
-- default so the column matches what create_all emits (no server default).
ALTER TABLE exercise ADD COLUMN IF NOT EXISTS exercise_hints JSON;
UPDATE exercise SET exercise_hints = '[]'::json WHERE exercise_hints IS NULL;
ALTER TABLE exercise ALTER COLUMN exercise_hints SET NOT NULL;
