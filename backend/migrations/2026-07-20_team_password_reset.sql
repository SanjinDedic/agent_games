-- One-time password-reset links: the owning institution generates a token for
-- a team and shares the /reset/<token> page; the student sets a new password
-- there, which consumes the token.
ALTER TABLE team ADD COLUMN IF NOT EXISTS password_reset_token VARCHAR;
ALTER TABLE team ADD COLUMN IF NOT EXISTS password_reset_expiry TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS ix_team_password_reset_token ON team (password_reset_token);
