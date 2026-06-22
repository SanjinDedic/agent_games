-- Move all subscription/billing/Stripe state off `institution` into a dedicated
-- 1:1 `institution_subscription` table (clean separation of concerns: the
-- institution row is operational identity only; this row is everything about how
-- access is paid for and when it expires).
--
-- Idempotent. On a fresh DB, create_all() builds institution_subscription from
-- the model and `institution` never had the moved columns, so the backfill/drop
-- block below is skipped entirely. Supersedes the old payment_client table.

CREATE TABLE IF NOT EXISTS institution_subscription (
    id                          SERIAL PRIMARY KEY,
    institution_id              INTEGER NOT NULL UNIQUE REFERENCES institution (id),
    payment_method              VARCHAR NOT NULL DEFAULT 'admin',
    tier                        VARCHAR NULL,
    subscription_active         BOOLEAN NOT NULL DEFAULT TRUE,
    subscription_expiry         TIMESTAMPTZ NOT NULL,
    auto_renew                  BOOLEAN NOT NULL DEFAULT FALSE,
    stripe_customer_id          VARCHAR NULL,
    stripe_subscription_id      VARCHAR NULL,
    stripe_checkout_session_id  VARCHAR NULL,
    stripe_invoice_id           VARCHAR NULL,
    business_contact_name       VARCHAR NULL,
    business_contact_email      VARCHAR NULL,
    created_date                TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_institution_subscription_institution_id
  ON institution_subscription (institution_id);
-- One paid checkout session creates at most one institution.
CREATE UNIQUE INDEX IF NOT EXISTS ix_institution_subscription_stripe_checkout_session_id
  ON institution_subscription (stripe_checkout_session_id);
CREATE INDEX IF NOT EXISTS ix_institution_subscription_stripe_customer_id
  ON institution_subscription (stripe_customer_id);
CREATE INDEX IF NOT EXISTS ix_institution_subscription_stripe_subscription_id
  ON institution_subscription (stripe_subscription_id);
CREATE INDEX IF NOT EXISTS ix_institution_subscription_stripe_invoice_id
  ON institution_subscription (stripe_invoice_id);

-- Backfill one subscription row per existing institution from the legacy columns,
-- then drop those columns from `institution`. Guarded on the legacy column still
-- existing so the whole block is a no-op on fresh (create_all) databases and on
-- re-runs. Pre-existing institutions are admin-granted (no Stripe data), so the
-- Stripe IDs backfill as NULL.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'institution' AND column_name = 'subscription_active'
  ) THEN
    -- Only reference columns guaranteed to exist on a pre-PR institution
    -- (subscription_active/expiry/created_date). auto_renew and payment_method
    -- are set to literals: pre-existing institutions are admin-granted, and the
    -- target's NOT NULL auto_renew (when the table was built by create_all) has
    -- no server default, so it must be supplied explicitly.
    INSERT INTO institution_subscription
        (institution_id, payment_method, subscription_active, auto_renew,
         subscription_expiry, created_date)
    SELECT i.id, 'admin', i.subscription_active, FALSE,
           i.subscription_expiry, i.created_date
    FROM institution i
    WHERE NOT EXISTS (
        SELECT 1 FROM institution_subscription s WHERE s.institution_id = i.id
    );

    ALTER TABLE institution DROP COLUMN IF EXISTS subscription_active;
    ALTER TABLE institution DROP COLUMN IF EXISTS subscription_expiry;
    ALTER TABLE institution DROP COLUMN IF EXISTS auto_renew;
    ALTER TABLE institution DROP COLUMN IF EXISTS stripe_customer_id;
    ALTER TABLE institution DROP COLUMN IF EXISTS stripe_subscription_id;
    ALTER TABLE institution DROP COLUMN IF EXISTS stripe_checkout_session_id;
  END IF;
END $$;

-- payment_client is superseded by institution_subscription.
DROP TABLE IF EXISTS payment_client;
