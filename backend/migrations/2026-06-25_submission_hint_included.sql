-- Submission: add the hint_included flag recording whether a hint was
-- returned alongside the submission.
-- Idempotent: safe to run multiple times on existing DBs.
-- For fresh DBs, SQLModel.metadata.create_all() in init_db.py creates this
-- column automatically from the model definition; running this script is a
-- no-op in that case.

ALTER TABLE submission
  ADD COLUMN IF NOT EXISTS hint_included BOOLEAN NOT NULL DEFAULT FALSE;
