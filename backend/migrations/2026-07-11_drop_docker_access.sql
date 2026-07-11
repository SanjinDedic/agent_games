-- docker_access gated /institution/run-simulation and /diagnostics/status per
-- institution. All institutions now have the same permissions and must run
-- simulations, so the flag and its checks are removed.
ALTER TABLE institution DROP COLUMN IF EXISTS docker_access;
