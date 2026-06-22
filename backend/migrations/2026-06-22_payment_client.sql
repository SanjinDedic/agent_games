-- Invoiced institution signups: billing + teaching contacts and Stripe linkage
-- for institutions on the invoiced annual plan (collection_method=send_invoice).
-- Idempotent: safe to run multiple times. On a fresh DB, create_all() in
-- init_db.py builds this table from the PaymentClient model and this is a no-op.

CREATE TABLE IF NOT EXISTS payment_client (
    id                       SERIAL PRIMARY KEY,
    institution_id           INTEGER NULL REFERENCES institution (id),
    institution_name         VARCHAR NOT NULL,
    institution_address      VARCHAR NOT NULL,
    business_contact_name    VARCHAR NOT NULL,
    business_contact_email   VARCHAR NOT NULL,
    teaching_contact_name    VARCHAR NOT NULL,
    teaching_contact_email   VARCHAR NOT NULL,
    stripe_customer_id       VARCHAR NULL,
    stripe_subscription_id   VARCHAR NULL,
    stripe_invoice_id        VARCHAR NULL,
    created_date             TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_payment_client_institution_id
  ON payment_client (institution_id);
CREATE INDEX IF NOT EXISTS ix_payment_client_stripe_customer_id
  ON payment_client (stripe_customer_id);
CREATE INDEX IF NOT EXISTS ix_payment_client_stripe_subscription_id
  ON payment_client (stripe_subscription_id);
CREATE INDEX IF NOT EXISTS ix_payment_client_stripe_invoice_id
  ON payment_client (stripe_invoice_id);
