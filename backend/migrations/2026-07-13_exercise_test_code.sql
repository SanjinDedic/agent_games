-- Exercises are now tested by an admin-trusted Python test script
-- (see backend/tasks/exercise_test_code.py); the declarative JSON
-- test_cases column is obsolete and dropped without back-compat.
ALTER TABLE exercise ADD COLUMN IF NOT EXISTS test_code TEXT;
ALTER TABLE exercise DROP COLUMN IF EXISTS test_cases;
