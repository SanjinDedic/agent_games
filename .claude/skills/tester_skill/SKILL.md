---
name: tester_skill
description: Run the full Playwright browser-test suite for agent_games via ./run_playwright_tests.sh and analyze the failures. Use when asked to test the app locally, run the browser/manual tests, or verify the stack works end-to-end.
---

# Browser test run + failure analysis

One job: run the suite through the runner script, then explain what failed and why.

The script owns ALL setup — Playwright install/check (permanent install in
`~/.agent-games-playwright`, never inside the repo), `.env` sourcing, stack
reset. Do not install Playwright or run docker compose commands yourself.

## 1. Run

```bash
# from the repo root
./run_playwright_tests.sh all
```

`all` = non-interactive: headless, every stage in order, per-stage
summary at the end, exit 1 if anything failed. Without `all` the script is an
interactive menu (browser mode, per-stage picker) — for humans, not for you.

Three stages, run in order and sharing state through
`/tmp/agent_games_manual_state.json`:

- **01 admin setup** — claim the deployment through the first-run setup form,
  create a league and two teams, assign them.
- **02 team submissions** — each team logs in and submits an agent; one valid,
  one refused by the AST safety check.
- **03 admin progress** — the submissions grid shows both teams' work, and a
  simulation runs over it.

The suite covers submission, simulation and the admin's view of progress, and
nothing else by design. Behaviour coverage lives in the pytest suite
(`docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm test-runner`);
a browser failure here means the whole stack is broken, not that an edge case
regressed.

**Warning before running:** every launch does `docker compose down -v` — wipes
the local database. Say so first unless the user explicitly asked for a
reset/clean run. Expect a few minutes (stack reset + healthcheck wait + three
stages, one of which runs a real simulation).

**Do not run it while a pytest run is in flight.** The test overlay recreates the
api and worker containers with `DB_ENVIRONMENT=test`, which pulls the stack out
from under the browser. Check with `docker ps | grep test-runner` first.

## 2. Analyze failures

For each FAIL in the summary:

- **Screenshot**: `/tmp/agent_games_STAGE<N>_failure.png` — read it.
- **Observed block**: each stage prints an `--- observed ---` JSON block
  (toasts, browser console errors) at the end of its output. A React render
  error in `consoleErrors` is the usual cause of a page that "never loads".
- **Backend logs**: `docker logs agent_games-api-1 --since 10m` (workers:
  `agent_games-worker-validation-1`, `agent_games-worker-simulation-1`).

There are no known-flaky stages. Every failure is a real one until proven
otherwise.

Stage ↔ script mapping and per-stage detail: `manual_tests/README.md`.

## 3. Report

Per-stage PASS/FAIL table, then for each failure: which step, what was
observed (toast / console error / API response), and the relevant log lines.
Declare the stack healthy when all three stages pass.
