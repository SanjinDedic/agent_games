-- Normalized schema snapshot for the CI drift gate (backend/check_schema_drift.sh).
--
-- Emits one line per schema object, sorted by name — never by OID or column
-- position. Ordering by position would false-positive: a column added to an
-- existing table by ALTER sits at a later attnum than the same column in a
-- fresh CREATE TABLE from the models.
--
-- Run with `psql -AtqX -f` against two databases and diff the outputs.

SELECT '== TABLES ==';
SELECT c.relname
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY 1;

SELECT '== COLUMNS ==';
SELECT c.relname || '.' || a.attname
       || '  type=' || format_type(a.atttypid, a.atttypmod)
       || '  notnull=' || a.attnotnull::text
       || '  default=' || COALESCE(pg_get_expr(d.adbin, d.adrelid), '<none>')
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
WHERE n.nspname = 'public' AND c.relkind = 'r'
  AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY 1;

-- contype 'n' (NOT NULL rows, new in Postgres 18's pg_constraint) is excluded:
-- nullability is already captured by the notnull= flag above.
SELECT '== CONSTRAINTS ==';
SELECT con.conrelid::regclass::text || ': ' || con.conname
       || ' ' || pg_get_constraintdef(con.oid)
FROM pg_constraint con
WHERE con.connamespace = 'public'::regnamespace
  AND con.contype <> 'n'
ORDER BY 1;

SELECT '== INDEXES ==';
SELECT indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY indexname;

-- The models create real Postgres enum types (teamtype, leaguetype, ...) and
-- create_all never ALTER TYPEs an existing one, so a new enum member needs a
-- migration — compare labels by presence. Sorted by label, not enumsortorder:
-- ALTER TYPE ... ADD VALUE may place a label at a different position than a
-- fresh CREATE TYPE from the models, and these enums are never order-compared.
SELECT '== ENUM LABELS ==';
SELECT t.typname || ': ' || e.enumlabel
FROM pg_enum e
JOIN pg_type t ON t.oid = e.enumtypid
JOIN pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname = 'public'
ORDER BY t.typname, e.enumlabel;
