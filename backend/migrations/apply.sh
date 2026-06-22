#!/bin/sh
#
# Apply every .sql migration in this folder in filename (date) order. Migrations
# are idempotent SQL (CREATE/ALTER ... IF NOT EXISTS), so this is safe to re-run.
# On a fresh database init_db.py builds the schema from the models and these
# migrations become no-ops.
#
# POSIX sh, NOT bash: the deployed container is Alpine and has no bash.
#
# Two auto-detected modes:
#   * $DATABASE_URL set (e.g. inside the deployed container): run psql directly
#     against it. The SQLAlchemy "+psycopg" driver suffix is stripped because the
#     psql CLI only accepts a libpq URI (postgresql://...). When run OUTSIDE a
#     container the internal "@postgres:" host is rewritten to "@localhost:",
#     mirroring backend/database/db_config.py.
#   * $DATABASE_URL unset (local dev): run psql inside the `postgres` docker
#     compose service (stack must be up). Optional DB name arg, default
#     agent_games.
#
# Usage:
#   backend/migrations/apply.sh                  # local dev -> agent_games
#   backend/migrations/apply.sh agent_games_test # local dev -> test DB
#   DATABASE_URL=... backend/migrations/apply.sh # against that URL directly
#
set -eu

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

# Turn a (possibly SQLAlchemy-style) DATABASE_URL into a libpq URL psql accepts.
normalize_url() {
    url=$1
    # postgresql+psycopg://... -> postgresql://...  (psql rejects the +driver)
    url=$(printf '%s' "$url" | sed 's#+psycopg##')
    # Outside a container the compose service name won't resolve; use localhost.
    if [ ! -e /.dockerenv ]; then
        url=$(printf '%s' "$url" | sed 's#@postgres:#@localhost:#')
    fi
    printf '%s' "$url"
}

# Iterate *.sql sorted by name (shell glob is lexical => date-prefix order).
apply_with_psql() {  # $1 = connection URL
    _url=$1
    _found=0
    for f in "$DIR"/*.sql; do
        [ -e "$f" ] || continue  # no matches: skip the literal glob
        _found=1
        echo "==> applying $(basename "$f")"
        psql "$_url" -v ON_ERROR_STOP=1 -f "$f"
    done
    [ "$_found" -eq 1 ] || echo "No .sql migrations found in $DIR"
}

apply_with_compose() {  # $1 = db name
    _db=$1
    _found=0
    for f in "$DIR"/*.sql; do
        [ -e "$f" ] || continue
        _found=1
        echo "==> applying $(basename "$f") to $_db"
        docker compose exec -T postgres psql -U postgres -d "$_db" \
            -v ON_ERROR_STOP=1 < "$f"
    done
    [ "$_found" -eq 1 ] || echo "No .sql migrations found in $DIR"
}

if [ -n "${DATABASE_URL:-}" ]; then
    apply_with_psql "$(normalize_url "$DATABASE_URL")"
    echo "All migrations applied via DATABASE_URL."
else
    DB="${1:-agent_games}"
    ROOT=$(CDPATH= cd -- "$DIR/../.." && pwd)
    cd "$ROOT"
    apply_with_compose "$DB"
    echo "All migrations applied to $DB."
fi
