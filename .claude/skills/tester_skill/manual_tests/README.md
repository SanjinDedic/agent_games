# Manual-test scripts (docs/integration-test-manual.md + classroom flow)

Deterministic Playwright scripts that execute the full integration-test manual against local dev
(`http://localhost:3000`), plus the teacher/classroom flow (not in the manual yet). Numbered by
run order — later scripts read values recorded by earlier ones (signup URLs, league id, team and
student credentials) from the state file (`STATE_FILE` env var, default
`/tmp/agent_games_manual_state.json`), mirroring the manual's Recording Sheet.

The platform serves two audiences with the same routes but different wording
(`frontend/src/AgentGames/Shared/terminology.js`, driven by the institution's `is_teacher` flag):

- **Competition flow** (institution + league + team wording): scripts 02–04
- **Classroom flow** (teacher + classroom + student wording): scripts 05–06

| Script | Flow | What it covers |
|--------|------|----------------|
| `01_admin_setup.js` | shared | manual Stage 1 — admin login, institutions ×2 + one **teacher account** (`is_teacher` checkbox; Type badge asserted) + delete ×1, backup/restore, OpenAI key (needs `OPENAI_API_KEY` env var), logout |
| `02_institution_league.js` | competition | manual Stage 2 — institution login (navbar must say "League Management", never classroom wording), create greedy_pig league, capture signup URL, attach the seeded tutorial |
| `03_team_submissions.js` | competition | manual Stage 3 — three teams: signup via the join page ("League · greedy_pig", "Team Name", "Sign Up & Join League"), 2 valid + 1 invalid submission, history check, logout; Team 1 also runs tutorial exercise #4 "Add Up the Scoreboard" end-to-end (TEAM: footer) |
| `04_institution_review_publish.js` | competition | manual Stage 4 — review submissions, plagiarism (OpenAI), 100-round simulation, publish + public page |
| `05_teacher_classroom.js` | classroom | mirror of 02 — teacher login via `/Teacher` ("Teacher Login", "Account Name:"; navbar must say "Classroom Management" / "Student Section"), create greedy_pig classroom ("Create Classroom", "Classroom Created Successfully"), capture join URL, attach the seeded tutorial |
| `06_student_submissions.js` | classroom | mirror of 03 — two students: signup via the classroom join page ("Classroom · greedy_pig", "Student Name", "Sign Up & Join Classroom"), same 2-valid + 1-invalid submissions and history check (STUDENT:/CLASSROOM: footer); Student 1 runs the same tutorial exercise (per-student progress, STUDENT: footer) |
| `07_demo_hints.js` | demo | manual Stage 5 — per game ×7: demo user, invalid submission, Get Hint, fix, valid submission |
| `08_password_reset.js` | classroom | not in the manual yet — teacher generates a one-time reset link for Student 1 (`/institution/team-password-reset`; modal must say "Share this link with the student."), regenerates (old link must 404), consumes the live link on `/reset/<token>` (mismatch check, then reset + auto-login via `/user/reset-team-password`), verifies work kept (stage 6's 2 submissions), consumed link dead, old password rejected / new password logs in |

```bash
# stack must be up (docker compose up -d); a wiped DB gives the cleanest run
# the tutorial (scripts 03 and 06) is NOT seeded on boot — seed it once per fresh DB
# from the private tutorial_data/ folder (pull from prod first if it's empty):
docker compose exec api python tutorial_data/tutorial_sync.py push --target local --link-all-leagues
export OPENAI_API_KEY=sk-...
for s in 01_admin_setup 02_institution_league 03_team_submissions \
         04_institution_review_publish 05_teacher_classroom \
         06_student_submissions 07_demo_hints 08_password_reset; do
  NODE_PATH="$HOME/.agent-games-playwright/node_modules" \
    node .claude/skills/tester_skill/manual_tests/$s.js || break
done
```

State-file dependencies: 02–04 need 01 (institution) and each other in order; 05 needs 01
(teacher account); 06 needs 05 (classroom join URL); 07 is independent; 08 needs 01 + 05 + 06
(teacher account, classroom name, student credentials — it rewrites Student 1's password in
the state file after the reset).

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
- Stage 5 (script 07): greedy_pig / prisoners_dilemma / arena_champions strictly reject the
  manual's "invalid" return (asserted each run — acceptance is a failure), then a syntax error
  drives the hint flow; the failed submission's response must advertise the hint immediately
  (asserted, no retry).
- Classroom copy that still says "league" (asserted as-is by 05/06): the student signup toast
  ("Signed up and joined league successfully!", hardcoded in `DirectClassicSignup.jsx`) and the
  Save Tutorials toast ("Tutorials updated for league '<name>'", backend message).
