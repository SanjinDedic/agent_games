-- Team.name is no longer globally unique.
--
-- Previously `ix_team_name` was a UNIQUE index, which made it the binding
-- constraint and prevented two different institutions from ever having a team
-- with the same name (e.g. "Team A"). Uniqueness is now scoped per-institution
-- via a new (name, institution_id) constraint — a name is a team's stable
-- identity within its institution as it moves between leagues. The existing
-- (name, league_id) constraint is kept as a secondary guard for teams whose
-- league has no institution (institution_id NULL), which Postgres unique treats
-- as distinct. The global unique index is replaced with a plain (non-unique)
-- index that still serves name lookups (team login, simulation attribution).
--
-- Idempotent: safe to run multiple times on existing DBs. On a fresh DB
-- init_db.py builds `ix_team_name` (non-unique) and both constraints directly
-- from the model, so this script is a no-op there.

-- Drop the old UNIQUE index and recreate it non-unique. DROP + CREATE (rather
-- than an in-place alter, which Postgres doesn't support for uniqueness) keeps
-- the same index name the ORM expects.
DROP INDEX IF EXISTS ix_team_name;
CREATE INDEX IF NOT EXISTS ix_team_name ON team (name);

-- Ensure both composite uniqueness constraints exist.
-- (name, league_id) predates this migration on most DBs; (name, institution_id)
-- is new. Adding (name, institution_id) is safe: the old global unique index
-- guaranteed all names were distinct, so no existing rows can violate it.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'team_name_league_id_key'
    ) THEN
        ALTER TABLE team
            ADD CONSTRAINT team_name_league_id_key UNIQUE (name, league_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'team_name_institution_id_key'
    ) THEN
        ALTER TABLE team
            ADD CONSTRAINT team_name_institution_id_key UNIQUE (name, institution_id);
    END IF;
END $$;
