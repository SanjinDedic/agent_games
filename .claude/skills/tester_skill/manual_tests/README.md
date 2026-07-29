# Manual-test scripts (docs/integration-test-manual.md + classroom flow)

Deterministic Playwright scripts that execute the full integration-test manual against local dev
(`http://localhost:3000`), plus the teacher/classroom flow (not in the manual yet). Numbered by
run order — later scripts read values recorded by earlier ones (signup URLs, league id, team and
student credentials) from the state file (`STATE_FILE` env var, default
`/tmp/agent_games_manual_state.json`), mirroring the manual's Recording Sheet.

The platform serves two audiences with the same routes but different wording
(`frontend/src/AgentGames/Shared/terminology.js`, driven by the institution's `is_teacher` flag):

- **Competition flow** (institution + league + team wording): scripts 02–04
- **Classroom flow** (teacher + classroom + student wording): scripts 05–06, 08–09

Post-revamp layout (both flows): institution/teacher login lands on `/InstitutionHome`,
where leagues/classrooms are created (the `LeagueCreation` card + modal) and each is opened
into its `/Classroom/:id/:tab` workspace. Everything else — roster (**Students**/**Teams**),
**Tutorial Progress** (a teacher sees **Short Course Progress**), **Concepts**,
**Submissions**, **Simulation**, **Settings** (expiry, login page, tutorials, delete) —
lives behind that workspace's tabs, with a per-student page (`/Classroom/:id/student/:teamId`)
behind the grids. The old standalone `/InstitutionLeague`, `/InstitutionLeagueSimulation`
and `/InstitutionLeagueSubmissions` pages are gone (their routes now redirect into
Home/the workspace).

The student landing page (`/TeamHome`) leads with the agent game — placement squares
coloured off the same ramp as the teacher's grids, the valid-submission count, and the
attempts that never got past validation — and carries the tutorials/short courses under it.

| Script | Flow | What it covers |
|--------|------|----------------|
| `01_admin_setup.js` | shared | manual Stage 1 — admin login, institutions ×2 + one **teacher account** (`is_teacher` checkbox; Type badge asserted) + delete ×1, backup/restore, OpenAI key (needs `OPENAI_API_KEY` env var), logout |
| `02_institution_league.js` | competition | manual Stage 2 — institution login (lands on `/InstitutionHome`; navbar "Teams" + heading "Active Leagues", never classroom/student wording), create greedy_pig league from the Home "Create New League" card, capture signup URL, attach the seeded tutorial via the workspace **Settings** tab |
| `03_team_submissions.js` | competition | manual Stage 3 — three teams: signup via the join page ("League · greedy_pig", "Team Name", "Sign Up & Join League"), 2 valid + 1 invalid submission, history check, then the landing page reading the same three back (2 valid, 2 placement squares out of the field, the 1 rejected attempt), logout; Team 1 also runs the tutorial exercise "Add Up the Scoreboard" end-to-end (TEAM: footer) and checks its landing-page card |
| `04_institution_review_publish.js` | competition | manual Stage 4 — open the league workspace from Home, then its tabs: review submissions in the **Submissions** grid (one row per team, one cell per submission; a cell or **ALL** opens the code modal), plagiarism from inside that modal (OpenAI), 100-round simulation + publish (**Simulation**: runner → run summary → "Show results" modal), verify the public page |
| `05_teacher_classroom.js` | classroom | mirror of 02 — teacher login via `/Teacher` ("Teacher Login", "Account Name:"; lands on `/InstitutionHome`, navbar "Students" + heading "Active Classrooms"), create greedy_pig classroom from the Home "Create New Classroom" card ("Classroom Created Successfully"), capture join URL, attach the seeded tutorial via the workspace **Settings** tab (a teacher sees it as **Short Courses**) |
| `06_student_submissions.js` | classroom | mirror of 03 — two students: signup via the classroom join page ("Classroom · greedy_pig", "Student Name", "Sign Up & Join Classroom"), same 2-valid + 1-invalid submissions, history check and landing-page check (STUDENT:/CLASSROOM: footer, **Short Courses** section under the agent panel); Student 1 runs the same tutorial exercise, reached via the navbar's **Short Course** link (per-student progress, STUDENT: footer) |
| `07_demo_hints.js` | demo | manual Stage 5 — per game ×7: demo user, invalid submission, Get Hint, fix, valid submission |
| `08_password_reset.js` | classroom | not in the manual yet — teacher opens the classroom workspace **Students** tab and generates a one-time reset link for Student 1 (`/institution/team-password-reset`; modal must say "Share this link with the student."), regenerates (old link must 404), consumes the live link on `/reset/<token>` (mismatch check, then reset + auto-login via `/user/reset-team-password`), verifies work kept (stage 6's 2 submissions), consumed link dead, old password rejected / new password logs in |
| `09_teacher_progress.js` | classroom | not in the manual yet — the teacher-side readings of stages 05/06: the **Short Course Progress** grid (Student 1's single ✓ is the only pass, the Passed summary row agrees, a cell opens that student's exercise code), the **Concepts** map (Students × Concepts grid + Class row, coverage chips, "How is this worked out?", the concept modal from both a column heading and a student's cell, the two action lists), and the student page behind them (attempts run exactly one ahead of validated — the AST-rejected submission shows up nowhere else) |

```bash
# stack must be up (docker compose up -d); a wiped DB gives the cleanest run
# the tutorial (scripts 03 and 06) is NOT seeded on boot — seed it once per fresh DB
# from the private tutorial_data/ folder (pull from prod first if it's empty):
docker compose exec api python tutorial_data/tutorial_sync.py push --target local --link-all-leagues
export OPENAI_API_KEY=sk-...
for s in 01_admin_setup 02_institution_league 03_team_submissions \
         04_institution_review_publish 05_teacher_classroom \
         06_student_submissions 07_demo_hints 08_password_reset \
         09_teacher_progress; do
  NODE_PATH="$HOME/.agent-games-playwright/node_modules" \
    node .claude/skills/tester_skill/manual_tests/$s.js || break
done
```

State-file dependencies: 02–04 need 01 (institution) and each other in order; 05 needs 01
(teacher account); 06 needs 05 (classroom join URL); 07 is independent; 08 needs 01 + 05 + 06
(teacher account, classroom name, student credentials — it rewrites Student 1's password in
the state file after the reset); 09 needs 01 + 05 + 06 (it reads the classroom as the teacher
and asserts the work stage 6 did, so it must run after 06 — before or after 08 is immaterial,
it never logs in as a student).

Conventions (see `_helpers.js`):

- Playwright comes from the permanent install in `~/.agent-games-playwright` (never installed in
  the repo) — hence the `NODE_PATH` prefix.
- Every run records all react-toastify toasts, native dialog texts, and browser console errors,
  printed as an `--- observed ---` JSON block at the end; scripts exit non-zero on unexpected
  behavior and drop a screenshot in `/tmp/agent_games_STAGE<N>_failure.png`.
- Entity names carry a random run suffix so re-runs don't collide with existing rows.
- Tutorial content is authored outside this repo and moves: the exercise count and the position
  of "Add Up the Scoreboard" are read off the overview page (`readTutorialOverview` in
  `_helpers.js`) instead of being pinned, so adding an exercise doesn't fail stages 03/06. The
  exercise is still identified by title, and its starter code / 5 tests are asserted. Stage 09
  goes further and pins no content at all: exercise titles, concept names and their counts are
  read off the grids, and only their relationships are asserted.
- Placement numbers are a random game's output and are never asserted as values
  (`readAgentPanel` in `_helpers.js` reads them off each square's title). What stages 03/06
  assert is the shape: one square per valid submission, the best being the best of them,
  a placement inside the field size, and the 🏆 badge exactly when the best is 1st.
- Workspace tabs switch on the URL while the previous tab's table is still mounted, so stage 09
  binds each table by a row only it has (`Passed` for the progress grid, `Class` for the
  concepts grid) rather than by position, and waits for the classroom heading before clicking
  a tab at all (clicking a just-mounted tab strip can land before React attaches).
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
- Backend copy that still says "league"/"tutorials" for classrooms (asserted as-is by 05): the
  Save Short Courses toast, "Tutorials updated for league '<name>'". Frontend copy is fully
  terminology-aware — a teacher account calls tutorials **Short Courses**, and the student
  signup toast reads "Signed up and joined classroom successfully!".
- Stage 7 is subject to LLM nondeterminism: `hint_service._validate_hints` discards any hint
  whose `quoted_line` doesn't match the line number it claims, so an off-target model response
  turns into a 502 "LLM provider failed to generate a valid hint". Re-run before treating it as
  a regression.
