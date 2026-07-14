---
name: tester_skill
description: Set up local browser testing for agent_games — permanent Playwright install (outside the repo), clean app start from an empty DB, and a demo-submission smoke test. Use when asked to test the app locally, reset the local environment, or verify the stack works end-to-end before manual testing.
---

# Local testing setup + smoke test

Three phases: ensure Playwright is installed (one-time, permanent, outside the repo),
start the app from a clean database, run the smoke test. When the smoke test passes,
tell the user: **"Smoke test passed — I'm ready to test the app."**

## 1. Playwright (one-time, lives on the laptop, NOT in the repo)

The install lives in `~/.agent-games-playwright` (npm package) and
`~/Library/Caches/ms-playwright` (browsers). Nothing goes into the repo —
never `npm install playwright` inside the project.

Idempotent check + install:

```bash
if ! NODE_PATH="$HOME/.agent-games-playwright/node_modules" node -e "require('playwright')" 2>/dev/null; then
  mkdir -p ~/.agent-games-playwright && cd ~/.agent-games-playwright
  printf '{\n  "name": "agent-games-playwright",\n  "private": true,\n  "version": "1.0.0"\n}\n' > package.json
  npm install playwright
  npx playwright install chromium
fi
```

Gotcha: `npm init -y` fails there (directory name starts with a dot — invalid
package name), which is why the package.json is written by hand.

## 2. Clean app start (wipes the local DB!)

`down -v` deletes all volumes — Postgres data, MinIO objects. That is the point
(fresh DB, schema re-seeded by `init_db` + migrations on api boot), but say so
before running it if the user didn't explicitly ask for a reset.

```bash
cd /Users/sanjindedic/PROJECTS/agent_games
docker compose down -v --remove-orphans
docker compose up -d
```

`--remove-orphans` clears stale containers left by older compose files (e.g.
`simulator`/`validator`) or by test-overlay runs.

The tutorial (manual Stage 3.3 / `manual_tests/03_team_submissions.js`) is NOT
re-created by `init_db` — after a wipe, seed it with
`docker compose exec api python -m backend.scripts.seed_tutorial` (idempotent;
the smoke test doesn't need it).

Wait for readiness — poll, don't sleep (`timeout` doesn't exist on macOS):

```bash
# api (runs init_db + migrations first, then serves)
for i in $(seq 1 60); do curl -sf -o /dev/null http://localhost:8000/docs && break; sleep 2; done
# frontend (Vite)
for i in $(seq 1 60); do curl -sf -o /dev/null http://localhost:3000 && break; sleep 2; done
# workers must be healthy or submissions will hang
docker compose ps --format '{{.Name}} {{.Status}}'
```

All of api, frontend, postgres, valkey, minio, worker-validation,
worker-simulation should show `healthy` (frontend has no healthcheck — `Up` is
fine). If a submission later fails with a DB error like
`relation "..." does not exist`, the containers are pointing at the test DB:
check `docker exec agent_games-api-1 env | grep DB_ENVIRONMENT` — it must NOT
be `test` (dev default is `production`). Fix with
`docker compose up -d --force-recreate api worker-validation worker-simulation`
(no test overlay).

## 3. Smoke test (demo signup → valid submission → logout)

```bash
cd /Users/sanjindedic/PROJECTS/agent_games
NODE_PATH="$HOME/.agent-games-playwright/node_modules" node .claude/skills/tester_skill/smoke_test.js
```

The script signs up a uniquely-named demo team, joins `greedy_pig_demo`
(demo leagues are auto-created by the launch endpoint — an empty league table
is fine), waits for the Monaco editor to load the starter code, submits it
unchanged, asserts the API returns `status: "success"`, and logs out.
It prints `SMOKE TEST PASSED` and exits 0 on success. On failure it exits 1
and dumps a full-page screenshot to `/tmp/agent_games_smoke_failure.png` —
read it, then check `docker logs agent_games-api-1 --since 5m`.

Driving notes baked into the script (relevant if you edit it):

- Monaco is a React-controlled editor; set code via
  `window.monaco.editor.getEditors()[0].setValue(...)` in `page.evaluate` —
  DOM typing/`el.value` doesn't reliably fire React's onChange.
- Monaco loads from a CDN (`@monaco-editor/react` loader), so the headless
  browser needs internet access.
- Assert submission outcomes from the `/user/submit-agent` response body
  (`waitForResponse`), not the UI; toasts are timing-sensitive.
- Team names: alphanumeric, max 10 chars.

## 4. Report

- Pass → tell the user: **"Smoke test passed — I'm ready to test the app."**
- Fail → report which step failed, the failure screenshot path, and the
  relevant api/worker log lines. Do not declare readiness.

For speed/performance benchmarking against production, see the `benchmark_prod` skill.
