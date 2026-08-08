-- Rename the single-account table `owner` -> `admin`.
--
-- The single-tenant conversion first called the one account that runs a
-- deployment the "owner"; it is now the "admin" everywhere (role claim, route
-- prefix, table). create_all never renames, so a database created while the
-- table was still `owner` needs this. On a fresh volume both branches are
-- false and the file is a no-op.
--
-- Idempotent: renames only when `owner` exists and `admin` does not. If both
-- somehow exist, `owner` is left alone rather than silently dropped — that is a
-- state a human should look at.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'owner'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'admin'
    ) THEN
        ALTER TABLE public.owner RENAME TO admin;
    END IF;
END $$;
