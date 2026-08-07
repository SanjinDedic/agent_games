-- Drop the payment/subscription and tutorial/lesson/exercise schema.
--
-- The platform is now a locally-run hobby project: institutions have no
-- billing or access window, and the tutorial content library (tutorials,
-- exercises, lessons, concepts and every submission/progress row derived
-- from them) is gone. These tables are no longer defined by the models, so
-- create_all will never rebuild them — this drops them from databases that
-- predate the removal. CASCADE clears the FKs between them in one pass.
-- Idempotent: IF EXISTS makes re-running on every boot a no-op.

DROP TABLE IF EXISTS lessonconcept CASCADE;
DROP TABLE IF EXISTS exerciseconcept CASCADE;
DROP TABLE IF EXISTS concept CASCADE;
DROP TABLE IF EXISTS lesson CASCADE;
DROP TABLE IF EXISTS exercisehintreveal CASCADE;
DROP TABLE IF EXISTS exercisesubmission CASCADE;
DROP TABLE IF EXISTS exercisesubmissionmetadata CASCADE;
DROP TABLE IF EXISTS exercise CASCADE;
DROP TABLE IF EXISTS leaguetutorial CASCADE;
DROP TABLE IF EXISTS tutorial CASCADE;

DROP TABLE IF EXISTS institution_subscription CASCADE;
