#!/usr/bin/env bash
# Interactive runner for the Playwright manual-test stages in
# .claude/skills/tester_skill/manual_tests/ (see the README there).
#
# Sources .env, pulls OPENAI_API_KEY from .kamal/secrets when .env doesn't
# provide one (stage 1.5 validates it against OpenAI), points NODE_PATH at the
# permanent Playwright install, then loops: pick a stage, run it, back to the
# menu. Stages share state via /tmp/agent_games_manual_state.json — run 01
# before 02-05.
#
# Every launch resets the stack first: docker compose down -v, up -d --wait
# (blocks until the api healthcheck passes, i.e. init_db + migrations are
# done), then seeds the tutorial (Stage 3.3 needs it; not seeded on boot).
set -uo pipefail
cd "$(dirname "$0")"

set -a
source .env
set +a

if [[ -z "${OPENAI_API_KEY:-}" && -f .kamal/secrets ]]; then
  OPENAI_API_KEY="$(grep -m1 '^OPENAI_API_KEY=' .kamal/secrets | cut -d= -f2-)"
  export OPENAI_API_KEY
fi
[[ -n "${OPENAI_API_KEY:-}" ]] || echo "WARNING: no OPENAI_API_KEY found (.env / .kamal/secrets) — stage 1.5 will fail"

export NODE_PATH="$HOME/.agent-games-playwright/node_modules"

TESTS_DIR=".claude/skills/tester_skill/manual_tests"
PS3="> "

echo "=== resetting stack (docker compose down -v && up) ==="
docker compose down -v || { echo "docker compose down -v failed"; exit 1; }
docker compose up -d --wait || { echo "docker compose up failed"; exit 1; }

# Fresh DB invalidates any state recorded by a previous run
rm -f "${STATE_FILE:-/tmp/agent_games_manual_state.json}"

echo "=== seeding tutorial ==="
docker compose exec api python -m backend.scripts.seed_tutorial \
  || { echo "tutorial seed failed"; exit 1; }

echo "Browser mode:"
select mode in "headed — visible browser, SLOWMO=200ms" "headless — no window, full speed"; do
  case "$REPLY" in
    1) export HEADED=1 SLOWMO=200; break ;;
    2) unset HEADED; export SLOWMO=0; break ;;
    *) echo "pick 1 or 2" ;;
  esac
done

scripts=()
for f in "$TESTS_DIR"/[0-9]*.js; do
  scripts+=("$(basename "$f")")
done

echo
echo "Run mode:"
select run_mode in "full run — all stages in order, summary at end" "individual — pick tests from a menu"; do
  case "$REPLY" in
    1|2) break ;;
    *) echo "pick 1 or 2" ;;
  esac
done

# Full run: every stage runs even after a failure (stage 01's known 1.4
# backup/restore failure exits 1 in local dev but still records the state
# later stages need), then a per-stage summary; exit 1 if anything failed.
if [[ "$REPLY" == "1" ]]; then
  results=()
  failed=0
  for s in "${scripts[@]}"; do
    echo
    echo "=== running $s ==="
    if node "$TESTS_DIR/$s"; then
      results+=("PASS  $s")
    else
      results+=("FAIL  $s (exit $?)")
      failed=1
    fi
  done
  echo
  echo "=== full run summary ==="
  printf '%s\n' "${results[@]}"
  exit $failed
fi

while true; do
  echo
  echo "Pick a test (q to quit):"
  select s in "${scripts[@]}" "quit"; do
    [[ "${s:-}" == "quit" || "$REPLY" == "q" ]] && exit 0
    [[ -n "${s:-}" ]] || { echo "invalid choice"; break; }
    echo "=== running $s ==="
    if node "$TESTS_DIR/$s"; then
      echo "=== $s: PASS ==="
    else
      echo "=== $s: FAIL (exit $?) ==="
    fi
    break
  done
done
