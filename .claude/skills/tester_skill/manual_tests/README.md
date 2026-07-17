# Manual-test scripts (docs/integration-test-manual.md, Stages 1–5)

Deterministic Playwright scripts that execute the full integration-test manual against local dev
(`http://localhost:3000`). Numbered by stage; run them in order — later stages read values recorded
by earlier ones (signup URL, league id, team credentials) from the state file
(`STATE_FILE` env var, default `/tmp/agent_games_manual_state.json`), mirroring the manual's
Recording Sheet.

| Script | Manual stage |
|--------|--------------|
| `01_admin_setup.js` | 1 — admin login, institutions ×2 + delete ×1, backup/restore, OpenAI key (needs `OPENAI_API_KEY` env var), logout |
| `02_institution_league.js` | 2 — institution login, create greedy_pig league, capture signup URL, attach the seeded tutorial to the league (2.3 — teams only see attached tutorials) |
| `03_team_submissions.js` | 3 — three teams: signup, 2 valid + 1 invalid submission, history check, logout; Team 1 also runs tutorial exercise #4 "Add Up the Scoreboard" end-to-end (3.3: fail 0/5 → pass 5/5 → broken code 400s → overview Completed / 1 of 10) |
| `04_institution_review_publish.js` | 4 — review submissions, plagiarism (OpenAI), 100-round simulation, publish + public page |
| `05_demo_hints.js` | 5 — per game ×7: demo user, invalid submission, Get Hint, fix, valid submission |

```bash
# stack must be up (docker compose up -d); a wiped DB gives the cleanest run
# the tutorial (Stage 3.3) is NOT seeded on boot — seed it once per fresh DB
# from the private tutorial_data/ folder (pull from prod first if it's empty):
docker compose exec api python tutorial_data/tutorial_sync.py push --target local --link-all-leagues
export OPENAI_API_KEY=sk-...
for s in 01_admin_setup 02_institution_league 03_team_submissions \
         04_institution_review_publish 05_demo_hints; do
  NODE_PATH="$HOME/.agent-games-playwright/node_modules" \
    node .claude/skills/tester_skill/manual_tests/$s.js || break
done
```

Conventions (see `_helpers.js`):

- Playwright comes from the permanent install in `~/.agent-games-playwright` (never installed in
  the repo) — hence the `NODE_PATH` prefix.
- Every run records all react-toastify toasts, native dialog texts, and browser console errors,
  printed as an `--- observed ---` JSON block at the end; scripts exit non-zero on unexpected
  behavior and drop a screenshot in `/tmp/agent_games_STAGE<N>_failure.png`.
- Entity names carry a random run suffix so re-runs don't collide with existing rows.
- Monaco is driven via `window.monaco.editor.getEditors()[0].setValue(...)`; submission outcomes
  are asserted from the `/user/submit-agent` response body (200 + `submission_id` = valid,
  400 + `detail` = failed validation), not from the UI. Tutorial exercise submissions are
  asserted the same way from `/tutorial/submit-exercise` (200 + `passed`/`test_results`;
  400 + `detail` when the code never produces results — a syntax error, a missing entry
  function, or a timeout). Exercises have NO AST safety gate by design: the slim
  exercise-worker container is the sandbox, so `import os` is allowed there.

Known app-side deviations the scripts expect and document (full detail in
`docs/test_findings/integration-manual-run-2026-07-11.md`):

- Stage 4.5 first gets a 403 (simulation requires Docker access, manual says leave it unchecked);
  the script enables the toggle via the admin UI and retries.
- Stage 5: greedy_pig / prisoners_dilemma / arena_champions strictly reject the manual's "invalid"
  return (asserted each run — acceptance is a failure), then a syntax error drives the hint flow;
  the failed submission's response must advertise the hint immediately (asserted, no retry).
