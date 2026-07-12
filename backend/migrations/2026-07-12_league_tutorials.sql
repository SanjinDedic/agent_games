-- Leagues now have 0..many tutorials via the leaguetutorial link table, and
-- teams only see the tutorials attached to their league.
--
-- Before this change every team saw every tutorial, so the first run
-- backfills a link row for every existing (league, tutorial) pair to preserve
-- what teams could already see. The backfill runs ONLY when the table is
-- first created: migrations re-run on every boot, and an unconditional
-- backfill would silently re-attach tutorials an admin had detached.
--
-- Idempotent: once the table exists this whole script is a no-op. On a fresh
-- DB init_db.py creates the table from the model first, so the backfill is
-- skipped there too (a fresh DB has no leagues or tutorials to link anyway).

DO $$
BEGIN
    IF to_regclass('public.leaguetutorial') IS NULL THEN
        CREATE TABLE leaguetutorial (
            id SERIAL PRIMARY KEY,
            league_id INTEGER NOT NULL REFERENCES league (id),
            tutorial_id INTEGER NOT NULL REFERENCES tutorial (id),
            CONSTRAINT leaguetutorial_league_id_tutorial_id_key
                UNIQUE (league_id, tutorial_id)
        );
        CREATE INDEX ix_leaguetutorial_league_id
            ON leaguetutorial (league_id);
        CREATE INDEX ix_leaguetutorial_tutorial_id
            ON leaguetutorial (tutorial_id);

        INSERT INTO leaguetutorial (league_id, tutorial_id)
        SELECT l.id, t.id FROM league l CROSS JOIN tutorial t;
    END IF;
END $$;
