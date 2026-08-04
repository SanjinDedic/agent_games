-- Code environment usage counters: per-user tallies of where submitted code
-- executed — browser Pyodide (WASM) vs the server path (Lambda). One row per
-- (user, kind, environment); every game/exercise submission endpoint bumps
-- call_count after its rate limit. Aggregated by /admin/code-env-stats for
-- the admin "Code Env" tab.
--
-- user_identifier is the team name as a plain string, deliberately without a
-- foreign key: demo teams and their submission rows are routinely deleted,
-- and these counters exist precisely to keep counting that traffic after the
-- cleanup. Nothing more granular than users and call totals is stored.
--
-- Matches what create_all emits for the CodeEnvUsage model: last_used is
-- nullable because the model supplies the default, call_count's default is
-- Python-side only (so NOT NULL without a server default), and the
-- UniqueConstraint becomes a table constraint rather than an index.
--
-- Idempotent: once the table exists this whole script is a no-op. Counters
-- start at zero — traffic before this migration was never recorded anywhere.

DO $$
BEGIN
    IF to_regclass('public.codeenvusage') IS NULL THEN
        CREATE TABLE codeenvusage (
            id SERIAL PRIMARY KEY,
            user_identifier VARCHAR NOT NULL,
            kind VARCHAR NOT NULL,
            environment VARCHAR NOT NULL,
            call_count INTEGER NOT NULL,
            last_used TIMESTAMP WITH TIME ZONE,
            CONSTRAINT codeenvusage_user_identifier_kind_environment_key
                UNIQUE (user_identifier, kind, environment)
        );
        CREATE INDEX ix_codeenvusage_user_identifier
            ON codeenvusage (user_identifier);
    END IF;
END $$;
