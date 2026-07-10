#!/bin/sh
#
# CI schema-drift gate: verifies that production's schema, after the entrypoint
# pre-start runs on deploy, will exactly match the SQLModel models being shipped.
#
# Inputs (set by the schema-drift job in .github/workflows/tests_coverage_deploy.yml):
#   ACTUAL_DATABASE_URL   — scratch DB pre-loaded with `pg_dump --schema-only`
#                           of production
#   EXPECTED_DATABASE_URL — empty scratch DB
#
# Steps:
#   1. Rehearse the schema half of backend/entrypoint.sh on the prod copy:
#      create_all (builds missing tables) + backend/migrations/*.sql (the
#      ALTERs). Seeding is skipped — it's data, not schema, and would run here
#      only because the schema-only copy has no rows (prod, already seeded,
#      no-ops it).
#   2. Build the expected schema in one shot from the models — exactly how a
#      fresh database (and the test suite) gets it.
#   3. Diff normalized catalog snapshots (backend/database/schema_snapshot.sql)
#      of the two databases. Any difference means a model change without a
#      matching migration, or a manual production edit → exit 1, blocking deploy.
#
# POSIX sh; runs inside the api image (psql via postgresql18-client).
set -eu

: "${ACTUAL_DATABASE_URL:?set to the prod-schema-copy database URL}"
: "${EXPECTED_DATABASE_URL:?set to an empty scratch database URL}"

# get_database_url() must read DATABASE_URL from the env, not the test shortcut
export DB_ENVIRONMENT=production

# psql wants libpq URLs; strip the SQLAlchemy "+psycopg" driver suffix
# (same rewrite as backend/entrypoint.sh)
ACTUAL_PSQL_URL=$(printf '%s' "$ACTUAL_DATABASE_URL" | sed 's/+psycopg//')
EXPECTED_PSQL_URL=$(printf '%s' "$EXPECTED_DATABASE_URL" | sed 's/+psycopg//')

# The same create_all that backend/database/init_db.py runs in the entrypoint:
# builds MISSING tables from the models, never ALTERs existing ones.
create_all() {
    DATABASE_URL="$1" python -c "
import backend.database.db_models  # register every table on SQLModel.metadata
from sqlmodel import SQLModel
from backend.database.db_session import get_db_engine
SQLModel.metadata.create_all(get_db_engine())
"
}

echo '==> prod copy: create_all (missing tables)'
create_all "$ACTUAL_DATABASE_URL"

for migration in backend/migrations/*.sql; do
    [ -e "$migration" ] || continue  # no matches: skip the literal glob
    echo "==> prod copy: applying migration $(basename "$migration")"
    psql "$ACTUAL_PSQL_URL" -q -v ON_ERROR_STOP=1 -f "$migration"
done

echo '==> expected: create_all on empty database'
create_all "$EXPECTED_DATABASE_URL"

echo '==> diffing schema snapshots'
SNAPSHOT=backend/database/schema_snapshot.sql
psql "$ACTUAL_PSQL_URL" -AtqX -v ON_ERROR_STOP=1 -f "$SNAPSHOT" > /tmp/schema_actual.txt
psql "$EXPECTED_PSQL_URL" -AtqX -v ON_ERROR_STOP=1 -f "$SNAPSHOT" > /tmp/schema_expected.txt

if diff -u /tmp/schema_expected.txt /tmp/schema_actual.txt; then
    echo '==> OK: production schema (after pre-start) matches the models'
else
    cat >&2 <<'EOF'

==> SCHEMA DRIFT DETECTED — deploy blocked.
Lines with '-' exist only in the models (expected); lines with '+' exist only
in production after the pre-start rehearsal (actual). A '-' usually means a
model change is missing its backend/migrations/*.sql (create_all never ALTERs
existing tables); a '+' usually means a manual production edit or a migration
the models no longer match.
EOF
    exit 1
fi
