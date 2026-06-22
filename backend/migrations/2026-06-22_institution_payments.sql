-- Institution payments: add address, auto_renew, and Stripe linkage columns.
-- Idempotent: safe to run multiple times on existing DBs.
-- For fresh DBs, SQLModel.metadata.create_all() in init_db.py creates these
-- columns automatically from the model definition; running this script is a
-- no-op in that case.

ALTER TABLE institution
  ADD COLUMN IF NOT EXISTS address VARCHAR NULL;

ALTER TABLE institution
  ADD COLUMN IF NOT EXISTS auto_renew BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE institution
  ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR NULL;

ALTER TABLE institution
  ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR NULL;

ALTER TABLE institution
  ADD COLUMN IF NOT EXISTS stripe_checkout_session_id VARCHAR NULL;

-- Unique guard so one paid checkout session creates at most one institution.
CREATE UNIQUE INDEX IF NOT EXISTS ix_institution_stripe_checkout_session_id
  ON institution (stripe_checkout_session_id);

CREATE INDEX IF NOT EXISTS ix_institution_stripe_customer_id
  ON institution (stripe_customer_id);

CREATE INDEX IF NOT EXISTS ix_institution_stripe_subscription_id
  ON institution (stripe_subscription_id);
