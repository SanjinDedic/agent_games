-- School leagues: add school_league flag and schools_config JSON column.
-- Idempotent: safe to run multiple times on existing DBs.
-- For fresh DBs, SQLModel.metadata.create_all() in init_db.py creates these
-- columns automatically from the model definition; running this script is a
-- no-op in that case.

ALTER TABLE league
  ADD COLUMN IF NOT EXISTS school_league BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE league
  ADD COLUMN IF NOT EXISTS schools_config JSON NULL;
