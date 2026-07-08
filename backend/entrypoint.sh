#!/bin/sh
#
# API/web pre-start, then hand off to the server.
#
# Runs the one-shot schema setup ONCE per container start (never from the app
# lifespan — every gunicorn worker runs the lifespan, so init there races across
# workers), then execs the server so it becomes PID 1 and receives signals
# directly. The server is taken from the arguments ($@ — uvicorn in dev);
# with no arguments (the Dockerfile CMD) it defaults to production gunicorn.
#
# Sequence; each step gates the next (set -e) so a bad deploy fails fast and
# never serves traffic:
#   1. init_db    — create missing tables from the models + seed initial data.
#                   Idempotent and Postgres-advisory-locked. create_all only
#                   builds MISSING tables; it never ALTERs existing ones.
#   2. migrations — apply every backend/migrations/*.sql in filename (date)
#                   order. They are idempotent (CREATE/ALTER ... IF NOT EXISTS,
#                   guarded DO blocks) and carry the ALTERs to existing tables
#                   that create_all can't do. On a fresh DB they are no-ops.
#
# POSIX sh (the Alpine runtime image has no bash). Invoked explicitly from the
# api CMD / compose command, NOT as a baked-in ENTRYPOINT: the worker and
# test-runner containers share this image and must NOT run this pre-start.
set -eu

# psql wants a libpq URL; strip the SQLAlchemy "+psycopg" driver suffix the
# app's DATABASE_URL carries. Runs inside the container, so no host rewrite is
# needed. The fallback matches backend/database/db_config.py.
DB_URL=$(printf '%s' "${DATABASE_URL:-postgresql://postgres:local_pw@postgres:5432/agent_games}" | sed 's/+psycopg//')

echo "==> init_db: ensuring schema + seed data"
python -m backend.database.init_db

for migration in backend/migrations/*.sql; do
    [ -e "$migration" ] || continue  # no matches: skip the literal glob
    echo "==> applying migration $(basename "$migration")"
    psql "$DB_URL" -v ON_ERROR_STOP=1 -f "$migration"
done

if [ $# -eq 0 ]; then
    # Production default (the Dockerfile CMD passes no args). Dev compose passes
    # an explicit server (uvicorn --reload) instead.
    set -- gunicorn backend.api:app \
        --worker-class uvicorn.workers.UvicornWorker \
        --workers "${GUNICORN_WORKERS:-3}" \
        --timeout "${GUNICORN_TIMEOUT:-300}" \
        --bind 0.0.0.0:8000 \
        --access-logfile - --error-logfile -
fi

echo "==> pre-start complete; starting server: $*"
exec "$@"
