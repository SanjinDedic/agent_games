#!/usr/bin/env bash
#
# Apply every .sql migration in this folder against a local database, in
# filename order. Migrations are plain idempotent SQL (CREATE/ALTER ... IF NOT
# EXISTS), so this is safe to re-run. On a fresh database, init_db.py builds the
# schema from the SQLModel models and these migrations become no-ops.
#
# Runs psql inside the `postgres` service via docker compose, so the stack must
# be up (`docker compose up -d`).
#
# Usage:
#   backend/migrations/apply.sh                 # apply to agent_games (default)
#   backend/migrations/apply.sh agent_games_test
#
set -euo pipefail

DB="${1:-agent_games}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"   # repo root (where docker-compose.yml lives)

shopt -s nullglob
files=("$DIR"/*.sql)
if [ "${#files[@]}" -eq 0 ]; then
    echo "No .sql migrations found in $DIR"
    exit 0
fi

cd "$ROOT"
# Sort by filename so date-prefixed migrations apply in chronological order.
while IFS= read -r f; do
    echo "==> applying $(basename "$f") to $DB"
    docker compose exec -T postgres psql -U postgres -d "$DB" -v ON_ERROR_STOP=1 < "$f"
done < <(printf '%s\n' "${files[@]}" | sort)

echo "All migrations applied to $DB."
