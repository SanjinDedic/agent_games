-- Concept.shortname: a few characters for column headings, where the full
-- name does not fit — the classroom Concepts grid puts one concept per column
-- and "The Accumulator Pattern" is not a column heading.
--
-- Nullable, no backfill: concepts authored before shortnames existed keep a
-- NULL and clients fall back to `name`. The values themselves are authored in
-- tutorial_data/concepts.json and arrive with the next tutorial_sync push.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS is a no-op once applied, and the
-- column is created here rather than in 2026-07-26_concepts.sql so a database
-- that already has the concept table also gets it.

ALTER TABLE concept ADD COLUMN IF NOT EXISTS shortname VARCHAR;
