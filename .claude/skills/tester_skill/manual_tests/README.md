# Browser test suite

Three Playwright scripts that drive local dev (`http://localhost:3000`) through the
one path the platform exists for: a team writes an agent, the agent competes, and
the admin can see both. Run them with `./run_playwright_tests.sh` from the repo
root — it resets the stack, then runs the stages in order.

Deliberately narrow. This is not a coverage net: the pytest suite
(`docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm test-runner`)
owns behaviour, and these scripts only answer "does the whole thing still work
through a real browser". Password resets, school leagues, AI hints, plagiarism
and publishing have no stage here on purpose.

Stages run in order and share state through `/tmp/agent_games_manual_state.json`
(`STATE_FILE` to override): stage 01 writes the admin, league and team
credentials that 02 and 03 log in with.

| Script | What it covers |
|--------|----------------|
| `01_admin_setup.js` | Claims the deployment through the first-run setup form at `/Login`, creates a greedy_pig league, creates two teams on `/Teams`, assigns both to the league from the Home page's Unassigned card, and reads the league id off the workspace URL. |
| `02_team_submissions.js` | Each team logs in at `/AgentLogin`, opens the agent workspace, and submits: the starter code (must store, `200` + `submission_id`), then the same code with `import os` prepended (must be refused by the AST check, `400` + "Unauthorized import: os"), then the good agent again so the team's latest is valid. |
| `03_admin_progress.js` | Admin logs in, checks the classroom workspace **Submissions** grid (one row per team, two graded submissions each), runs a 20-game simulation from the **Simulation** tab, and asserts every team's agent competed and the run landed in the summary panel. |

The single-admin model matters to how these read: one account runs the
deployment, and it is created by the setup form rather than seeded, so stage 01
must run against an unclaimed database. `run_playwright_tests.sh` guarantees that
with `docker compose down -v` plus `SEED_SAMPLE_DATA=false`.

Conventions (see `_helpers.js`):

- Playwright comes from the permanent install in `~/.agent-games-playwright` (never
  installed in the repo) — hence the `NODE_PATH` prefix when running a stage by hand:
  ```bash
  NODE_PATH="$HOME/.agent-games-playwright/node_modules" \
    node .claude/skills/tester_skill/manual_tests/01_admin_setup.js
  ```
- Every run records all react-toastify toasts and browser console errors, printed as
  an `--- observed ---` JSON block at the end. A stage exits non-zero on failure and
  drops a screenshot at `/tmp/agent_games_STAGE<N>_failure.png`.
- Entity names carry a random run suffix so a re-run against a surviving database
  doesn't collide with existing rows.
- Placements are the output of a random game and are never asserted as values — only
  that a placement was recorded at all.
- Monaco is driven via `window.monaco.editor.getEditors()[0].setValue(...)`; submission
  outcomes are read from the `/user/submit-agent` response body, not from the UI.
