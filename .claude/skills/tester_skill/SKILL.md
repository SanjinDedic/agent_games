---
name: tester_skill
description: Run the full Playwright browser-test suite for agent_games via ./run_playwright_tests.sh and analyze the failures. Use when asked to test the app locally, run the browser/manual tests, or verify the stack works end-to-end.
---

# Browser test run + failure analysis

One job: run the suite through the runner script, then explain what failed and why.

The script owns ALL setup — Playwright install/check (permanent install in
`~/.agent-games-playwright`, never inside the repo), `.env` + `OPENAI_API_KEY`
sourcing, stack reset, tutorial seeding. Do not install Playwright, run
docker compose commands, or seed anything yourself.

## 1. Run

```bash
cd /Users/slowturing/PROJECTS/agent_games
./run_playwright_tests.sh all
```

`all` = non-interactive: headless, every stage (01–05) in order, per-stage
summary at the end, exit 1 if anything failed. Without `all` the script is an
interactive menu (browser mode, per-stage picker) — for humans, not for you.

**Warning before running:** every launch does `docker compose down -v` — wipes
the local DB and MinIO volumes. Say so first unless the user explicitly asked
for a reset/clean run. Expect the full run to take several minutes (stack
reset + healthcheck wait + 5 stages).

## 2. Analyze failures

For each FAIL in the summary:

- **Screenshot**: `/tmp/agent_games_STAGE<N>_failure.png` — read it.
- **Observed block**: each stage prints an `--- observed ---` JSON block
  (toasts, native dialogs, browser console errors) at the end of its output.
- **Backend logs**: `docker logs agent_games-api-1 --since 10m` (workers:
  `agent_games-worker-validation-1`, `agent_games-worker-simulation-1`,
  `agent_games-worker-exercises-1`).
- **Known deviations** (expected, not regressions — full detail in
  `docs/test_findings/integration-manual-run-2026-07-11.md`):
  - Stage 1.4 backup/restore fails in local dev (backup S3 client ignores
    `S3_ENDPOINT_URL`) — stage 01 exits 1 but still records state for later
    stages; the runner continues.
  - Stage 1.5 needs `OPENAI_API_KEY` (script pulls it from `.env` or
    `.kamal/secrets`; it warns at startup if missing).
  - Stage 3.3 tutorial steps fail if the private `tutorial_data/` folder is
    missing — the script warns at seed time and tells you the pull command.
  - Stage 4.5 first gets a 403 (simulation Docker-access toggle); the script
    enables it via the admin UI and retries — not a failure.

Stage ↔ script mapping and per-stage detail: `manual_tests/README.md`.

## 3. Report

Per-stage PASS/FAIL table, then for each failure: which step, what was
observed (toast / console error / API response), the relevant log lines, and
whether it's a known deviation or a real regression. Declare the stack healthy
when stages 02–05 pass and stage 01's sole failure is the known 1.4
backup/restore.
