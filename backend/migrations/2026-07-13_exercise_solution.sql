-- Optional reference solution per exercise, used by the admin exercise
-- editor to verify the test script against a known-good implementation.
-- Never exposed to students.
ALTER TABLE exercise ADD COLUMN IF NOT EXISTS solution TEXT;
