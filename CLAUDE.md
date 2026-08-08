# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running tests
Tests run entirely via Docker Compose — no local Python/venv needed:

```bash
# Run all tests
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm test-runner

# Run a single test file
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm test-runner pytest backend/tests/integration/routes/auth/test_auth.py -v

# Run with coverage
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm test-runner pytest --cov=backend --cov-report=term backend/tests/
```

CI (`.github/workflows/tests.yml`) runs the same coverage command plus a frontend
`npm run build` on every push to `main` and every PR — no deploy step, this repo is
the self-hosted build.

### Running the app
```bash
# Development (starts api, valkey, celery workers, postgres, frontend)
# docker-compose.override.yml is applied automatically: it wraps the api in debugpy (port 5678)
docker compose up -d

# On api-container start, backend/entrypoint.sh runs the one-shot pre-start
# (idempotent, advisory-locked) before the server: init_db seeds the schema, then
# every backend/migrations/*.sql is applied. To re-run the whole sequence:
docker compose restart api

docker compose down   # Stop all containers
```

Compose requires `.env` at the repo root (committed dev defaults).

### Browser tests
```bash
./run_playwright_tests.sh all   # headless, three stages, exit 1 on failure
```
Three Playwright stages covering submission, simulation and the admin's view of
team progress — nothing else. See `.claude/skills/tester_skill/manual_tests/README.md`.
Every launch does `docker compose down -v`, and it must not overlap a pytest run
(the test overlay recreates the api/worker containers with `DB_ENVIRONMENT=test`).

### Frontend (standalone)
```bash
cd frontend
npm install
npm run dev      # Vite dev server on port 3000
npm run build    # Production build
```

### Database migrations
`backend/migrations/` holds dated SQL migration files, applied automatically on api-container boot by `backend/entrypoint.sh` (right after `init_db`, before the server starts). Migrations must be idempotent (`CREATE/ALTER ... IF NOT EXISTS`, guarded `DO` blocks) since they re-run on every boot. Tests do not run them — the test DB is built fresh from SQLModel metadata (`create_all`). When changing `db_models.py`, add a matching SQL migration so an existing local database picks the change up, and keep it in sync with the model if you later refactor those columns.

## Architecture

This is a **multi-game agent simulation platform** where students/teams submit code agents that compete in game simulations.

### Services (docker compose)
- **API** (port 8000): Main FastAPI app — auth, league/team management, agent submission, AI hints
- **Valkey** (port 6379): Redis-compatible Celery broker + result backend (ephemeral, no persistence)
- **worker-validation / worker-simulation**: Celery workers consuming the `validation` and `simulation` queues (separate containers so one queue's OOM can't kill the other's in-flight tasks)
- **PostgreSQL** (port 5432): Single cluster hosting both `agent_games` and `agent_games_test` databases
- **Frontend** (port 3000): React SPA served by Vite

Nothing talks to object storage: the frontend loads images and videos straight from
`VITE_ASSETS_URL` (a public bucket) and no backend code has an AWS dependency.

The API enqueues Celery tasks (`validation.run`, `simulation.run`) and awaits the result by polling the result backend (`backend/tasks/celery_utils.py`). Submitted code executes inside the worker containers (compose-level limits: 500MB RAM, 50 pids) with `worker_max_tasks_per_child=1` — a fresh process per task, so agent code can't contaminate later runs. The AST safety check runs in the API process before enqueue (`backend/routes/user/code_validation.py`); validation tasks have a 5s soft / 6s hard time limit (soft limit via `VALIDATION_TIMEOUT_SECONDS` env, hard is always soft+1; the test compose sets 2s/3s on worker-validation, so worker containers must be recreated with the test overlay after changing it).

### Backend structure (`backend/`)
- `api.py` — FastAPI entry point; mounts routers: auth, admin, user, agent, ai, diagnostics. Also serves the unauthenticated `GET /config` (site mode/name/icon and whether the deployment still needs claiming)
- `routes/` — Route modules grouped by domain. `admin/` is the whole operator surface (leagues, teams, simulations, publishing); `ai/` covers submission hints and plagiarism detection, with `ai/clients/` a pluggable provider layer — `AIClient` ABC + OpenAI/Anthropic/Google implementations registered in `factory.py`, keys stored per-provider in the DB
- `games/` — Game implementations extending `base_game.py`. Games are discovered dynamically: `backend/games/<name>/<name>.py` must define exactly one `BaseGame` subclass — no manual registration. Current games: `greedy_pig`, `prisoners_dilemma`, `lineup4`, `arena_champions`, `thirteen`, `breakthrough`, `hearts`, `ohhell`
- `database/` — SQLModel ORM models (`db_models.py`), DB config (`db_config.py`), session management, `init_db.py` for schema setup
- `migrations/` — dated SQL migrations for schema changes on an existing database (not used by tests)
- `tasks/` — All Celery code: `celery_app.py` (broker config, queue routing, worker settings), `celery_utils.py` (result polling), `validation_task.py` and `simulation_task.py` (the tasks)
- `Dockerfile` — shared image for api/workers/test-runner (build context is repo root)
- `config.py` — Central config: dynamic game discovery (`GAMES`), league expiry settings, secrets
- `time_utils.py` — The only place time/timezones are handled. All datetimes are aware UTC: get "now" via `utc_now()` (never `datetime.now()`/`datetime.utcnow()`), normalize boundary values with `ensure_utc()` (naive == UTC) or `interpret_as_sydney()` (naive user-typed dates == Sydney), convert for display with `to_sydney()`. DB columns are `TIMESTAMPTZ`; the frontend renders Sydney via moment-timezone. The Alpine image has no system tz database, so the `tzdata` PyPI package is a required dependency.

Python dependencies are managed with uv (`pyproject.toml` / `uv.lock`), Python 3.14.

### Frontend structure (`frontend/src/`)
- Vite + React 19. Monaco Editor for the in-browser code editor, Material-UI (v7) for components, Tailwind (v4) for utilities
- `AgentGames/` — Main feature area, organized by role: `Admin/` (the operator surface, including the `Classroom/` league workspace), `User/` (team-facing pages), `Shared/`, `Feedback/`
- `slices/` — Redux Toolkit slices: auth, feedback, games, leagues, rankings, settings, teams
- `components/` — Shared UI components
- `AgentGames/Shared/terminology.js` — one deployment serves one audience, set by `SITE_MODE`: a classroom (teacher/classroom/student wording) or a competition (organizer/league/team). Only user-visible copy goes through it — routes, JSON keys and Redux identifiers always say league/team

### Auth model
One tenant, so one operator account. Three roles: **admin** — the single account that runs the deployment (leagues, teams, keys, simulations); **student** and **ai_agent** — the two kinds of team session, split only by how they authenticate (a password versus an API key). JWT tokens with role-based route guards (`require_admin` / `require_team` / `require_agent` in `backend/routes/auth/auth_core.py`, `AuthProtection` on the frontend).

No admin account is seeded: a fresh deployment is unclaimed, `GET /config` reports `setup_required`, and the frontend shows the setup form at `/Login`. `POST /auth/setup` creates the one admin row and refuses once it exists. Everyone — admin and teams alike — then logs in through `POST /auth/login`, which resolves the name against the admin row first and the (globally unique) team names second, and reports which matched as `role`.

### Game framework
Each game extends `BaseGame` and implements match logic. `GameFactory` resolves game classes by folder-name convention at runtime. Games produce structured feedback (Markdown + JSON) shown in the frontend. `backend/games/game_instructions.md` documents how to add a new game.

### Testing
- Tests run inside a Docker container via `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm test-runner`
- Integration tests hit a real test database (`agent_games_test`) on the same Postgres instance — do not mock the database
- Task-level tests enqueue to the real broker and real workers (never `task_always_eager` — time limits and process isolation don't fire eager); use the `celery_workers` fixture to fail fast when workers are down
- `DB_ENVIRONMENT=test` is set automatically in the test-runner container (and on the workers via `docker-compose.test.yml`)
