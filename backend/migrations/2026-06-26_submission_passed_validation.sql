-- Submission: add the passed_validation flag recording whether a submission
-- passed validation and is safe to execute
-- Idempotent: safe to run multiple times on existing DBs.
-- For fresh DBs, SQLModel.metadata.create_all() in init_db.py creates this
-- column automatically from the model definition; running this script is a
-- no-op in that case.

ALTER TABLE submission
  ADD COLUMN IF NOT EXISTS passed_validation BOOLEAN NOT NULL DEFAULT TRUE;
