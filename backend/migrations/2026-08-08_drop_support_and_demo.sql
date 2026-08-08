-- Drop the support-ticket and demo-mode schema.
--
-- Both features are gone from the models, so create_all will never rebuild
-- them; this carries the change to databases that predate the removal.
--
-- The two is_demo columns are the load-bearing part. They are NOT NULL with no
-- server default, and the models no longer supply a value, so leaving them in
-- place turns every team and league INSERT into a NOT NULL violation. The table
-- drops are only tidiness by comparison — an unused table breaks nothing.
--
-- Idempotent: IF EXISTS makes re-running on every container start a no-op.

ALTER TABLE team DROP COLUMN IF EXISTS is_demo;
ALTER TABLE league DROP COLUMN IF EXISTS is_demo;

DROP TABLE IF EXISTS supportticketattachment CASCADE;
DROP TABLE IF EXISTS supportticket CASCADE;
DROP TYPE IF EXISTS supportticketcategory;
DROP TYPE IF EXISTS supportticketstatus;
DROP TYPE IF EXISTS supportticketsubmittertype;

DROP TABLE IF EXISTS demouser CASCADE;
