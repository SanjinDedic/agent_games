-- Institution: add the operational `address` column.
-- Subscription/billing/Stripe state is NOT stored here; see
-- 2026-06-22_institution_subscription.sql for the dedicated table.
-- Idempotent: safe to run multiple times. On a fresh DB,
-- SQLModel.metadata.create_all() in init_db.py adds this column from the model
-- and running this script is a no-op.

ALTER TABLE institution
  ADD COLUMN IF NOT EXISTS address VARCHAR NULL;
