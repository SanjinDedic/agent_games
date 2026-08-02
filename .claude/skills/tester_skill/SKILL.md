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
# from the repo root
./run_playwright_tests.sh all
```

`all` = non-interactive: headless, every stage (01–09) in order, per-stage
summary at the end, exit 1 if anything failed. Without `all` the script is an
interactive menu (browser mode, per-stage picker) — for humans, not for you.

Stage layout: 01 admin setup (institutions + teacher account), 02–04 the
COMPETITION flow (institution/league/team wording), 05–06 the CLASSROOM flow
(teacher/classroom/student wording — same routes, different labels), 07 the
demo hint loop, 08 the one-time student password-reset link, 09 the teacher's
progress dashboards over the work stage 06 did (short-course grid, concept
map, per-student page) — 08 and 09 are both classroom flow.

**Warning before running:** every launch does `docker compose down -v` — wipes
the local DB and MinIO volumes. Say so first unless the user explicitly asked
for a reset/clean run. Expect the full run to take several minutes (stack
reset + healthcheck wait + 9 stages).

## 2. Analyze failures

For each FAIL in the summary:

- **Screenshot**: `/tmp/agent_games_STAGE<N>_failure.png` — read it.
- **Observed block**: each stage prints an `--- observed ---` JSON block
  (toasts, native dialogs, browser console errors) at the end of its output.
- **Backend logs**: `docker logs agent_games-api-1 --since 10m` (server-side
  validation and exercise/snippet fallbacks all run inside the api container
  as local subprocesses — backend/validation_lambda/ and
  backend/fallback_lambda/; there is no worker container).
- **Known deviations** (expected, not regressions — full detail in
  `docs/test_findings/integration-manual-run-2026-07-11.md`):
  - Stage 1.5 needs `OPENAI_API_KEY` (script pulls it from `.env` or
    `.kamal/secrets`; it warns at startup if missing).
  - Stage 7 can fail with a 502 "LLM provider failed to generate a valid
    hint" on any game: `hint_service._validate_hints` drops every hint whose
    `quoted_line` doesn't match the line it claims, so an off-target model
    response leaves nothing to return. Intermittent — re-run the stage before
    calling it a regression.
  - The tutorial steps in stages 03 and 06 fail if the private
    `tutorial_data/` folder is missing — the script warns at seed time and
    tells you the pull command.
  - Stage 4.5 first gets a 403 (simulation Docker-access toggle); the script
    enables it via the admin UI and retries — not a failure.
  - Backend copy that still says "league"/"tutorials" for classrooms (stage 05
    asserts it as-is): the Save Short Courses toast, "Tutorials updated for
    league '<name>'". Frontend copy is terminology-aware throughout.

Stage ↔ script mapping and per-stage detail: `manual_tests/README.md`.

## 3. Report

Per-stage PASS/FAIL table, then for each failure: which step, what was
observed (toast / console error / API response), the relevant log lines, and
whether it's a known deviation or a real regression. Declare the stack healthy
when stages 01–08 all pass.
