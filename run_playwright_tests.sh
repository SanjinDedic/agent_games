#!/usr/bin/env bash
# Runner for the Playwright manual-test stages in
# .claude/skills/tester_skill/manual_tests/ (see the README there).
#
# Usage:
#   ./run_playwright_tests.sh        interactive: pick browser mode, then full
#                                    run or per-stage menu
#   ./run_playwright_tests.sh all    non-interactive: headless, every stage in
#                                    order, per-stage summary, exit 1 on failure
#
# Stages (see .claude/skills/tester_skill/manual_tests/README.md):
#   01 admin setup (institutions + teacher account)
#   02-04 COMPETITION flow: institution league -> team submissions -> review/publish
#   05-06 CLASSROOM flow: teacher classroom -> student submissions
#   07 demo hint loop
#   08 student password-reset link (classroom flow; needs 01 + 05 + 06)
#
# Owns all setup: ensures the permanent Playwright install (outside the repo),
# sources .env, pulls OPENAI_API_KEY from .kamal/secrets when .env doesn't
# provide one (stage 1.5 validates it against OpenAI). Stages share state via
# /tmp/agent_games_manual_state.json — run 01 before 02-08 (05 needs 01's
# teacher account; 06 needs 05's classroom join URL; 08 needs 06's students).
#
# Every launch resets the stack first: docker compose down -v, up -d --wait
# (blocks until the api healthcheck passes, i.e. init_db + migrations are
# done), then seeds the tutorial (the tutorial steps in stages 03 and 06
# need it; not seeded on boot).
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

# Playwright lives permanently OUTSIDE the repo: npm package in
# ~/.agent-games-playwright, browsers in ~/Library/Caches/ms-playwright.
# Never `npm install playwright` inside the project.
PLAYWRIGHT_HOME="$HOME/.agent-games-playwright"
export NODE_PATH="$PLAYWRIGHT_HOME/node_modules"
if ! node -e 'const fs=require("fs");process.exit(fs.existsSync(require("playwright").chromium.executablePath())?0:1)' 2>/dev/null; then
  echo "=== installing Playwright (one-time, $PLAYWRIGHT_HOME) ==="
  mkdir -p "$PLAYWRIGHT_HOME"
  # npm init -y fails here (dot-directory = invalid package name), so write package.json by hand
  [[ -f "$PLAYWRIGHT_HOME/package.json" ]] || printf '{\n  "name": "agent-games-playwright",\n  "private": true,\n  "version": "1.0.0"\n}\n' > "$PLAYWRIGHT_HOME/package.json"
  (cd "$PLAYWRIGHT_HOME" && npm install playwright && npx playwright install chromium) \
    || { echo "Playwright install failed"; exit 1; }
fi

TESTS_DIR=".claude/skills/tester_skill/manual_tests"
PS3="> "

echo "=== resetting stack (docker compose down -v && up) ==="
docker compose down -v || { echo "docker compose down -v failed"; exit 1; }
docker compose up -d --wait || { echo "docker compose up failed"; exit 1; }

# Fresh DB invalidates any state recorded by a previous run
rm -f "${STATE_FILE:-/tmp/agent_games_manual_state.json}"

echo "=== seeding tutorial ==="
if [[ -f tutorial_data/tutorial_sync.py ]]; then
  docker compose exec api python tutorial_data/tutorial_sync.py push --target local --link-all-leagues \
    || { echo "tutorial seed failed"; exit 1; }
else
  echo "WARNING: tutorial_data/ missing (private, gitignored) — the stage 03/06 tutorial steps will fail."
  echo "  Populate once with: docker compose run --rm --no-deps api python tutorial_data/tutorial_sync.py pull --target prod"
fi

scripts=()
for f in "$TESTS_DIR"/[0-9]*.js; do
  scripts+=("$(basename "$f")")
done

run_all=0
if [[ "${1:-}" == "all" ]]; then
  unset HEADED; export SLOWMO=0
  run_all=1
else
  echo "Browser mode:"
  select mode in "headed — visible browser, SLOWMO=200ms" "headless — no window, full speed"; do
    case "$REPLY" in
      1) export HEADED=1 SLOWMO=200; break ;;
      2) unset HEADED; export SLOWMO=0; break ;;
      *) echo "pick 1 or 2" ;;
    esac
  done

  echo
  echo "Run mode:"
  select run_mode in "full run — all stages in order, summary at end" "individual — pick tests from a menu"; do
    case "$REPLY" in
      1) run_all=1; break ;;
      2) run_all=0; break ;;
      *) echo "pick 1 or 2" ;;
    esac
  done
fi

# Full run: every stage runs even after a failure (stage 01's known 1.4
# backup/restore failure exits 1 in local dev but still records the state
# later stages need), then a per-stage summary; exit 1 if anything failed.
if [[ "$run_all" == 1 ]]; then
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
