-- Drop the school-league columns from `league`.
--
-- School leagues (curated school dropdown, Google-Sheets-backed roster,
-- server-assigned team names) were a multi-tenant feature. A local classroom or
-- club deployment has one operator who creates teams or shares a join link, so
-- the feature and both columns are gone. create_all never drops, so a database
-- created before this needs the statements below. On a fresh volume they are
-- no-ops.
--
-- Idempotent: IF EXISTS on both drops.
ALTER TABLE public.league DROP COLUMN IF EXISTS school_league;
ALTER TABLE public.league DROP COLUMN IF EXISTS schools_config;
