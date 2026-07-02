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

### Running the app
```bash
# Development (starts api, valkey, celery workers, postgres, minio, frontend)
# docker-compose.override.yml is applied automatically: it wraps the api in debugpy (port 5678)
docker compose up -d

# First-time DB init
docker compose exec api python -m backend.database.init_db

docker compose down   # Stop all containers
```

Compose requires `.env` at the repo root (committed dev defaults). An optional gitignored `.aws.env` overrides S3 credentials for devs exercising real S3 instead of MinIO.

### Frontend (standalone)
```bash
cd frontend
npm install
npm run dev      # Vite dev server on port 3000
npm run build    # Production build
```

### Database migrations
`backend/migrations/` holds dated SQL migration files, applied to existing databases via `apply.sh`. Tests do not run them — the test DB is built fresh from SQLModel metadata (`create_all`). When changing `db_models.py`, add a matching SQL migration for production.

## Architecture

This is a **multi-game agent simulation platform** where students/teams submit code agents that compete in game simulations.

### Services (docker compose)
- **API** (port 8000): Main FastAPI app — auth, league/team management, agent submission, AI hints, payments, support
- **Valkey** (port 6379): Redis-compatible Celery broker + result backend (ephemeral, no persistence)
- **worker-validation / worker-simulation**: Celery workers consuming the `validation` and `simulation` queues (separate containers so one queue's OOM can't kill the other's in-flight tasks)
- **PostgreSQL** (port 5432): Single cluster hosting both `agent_games` and `agent_games_test` databases
- **MinIO** (ports 9000/9001): Local S3-compatible storage for assets and support attachments (real S3 in production)
- **Frontend** (port 3000): React SPA served by Vite

The API enqueues Celery tasks (`validation.run`, `simulation.run`) and blocks on the result via `asyncio.to_thread(result.get)`. Submitted code executes inside the worker containers (compose-level limits: 500MB RAM, 50 pids) with `worker_max_tasks_per_child=1` — a fresh process per task, so agent code can't contaminate later runs. The AST safety check runs in the API process before enqueue (`backend/routes/user/code_validation.py`); validation tasks have a 5s soft / 8s hard time limit.

### Backend structure (`backend/`)
- `api.py` — FastAPI entry point; mounts routers: auth, admin, institution, user, agent, demo, ai, diagnostics, support, payments
- `routes/` — Route modules grouped by domain. Beyond CRUD domains: `ai/` (OpenAI-backed submission hints and plagiarism detection), `payments/` (Stripe checkout/webhooks for institution subscriptions), `support/` (support tickets with S3 attachments)
- `games/` — Game implementations extending `base_game.py`. Games are discovered dynamically: `backend/games/<name>/<name>.py` must define exactly one `BaseGame` subclass — no manual registration. Current games: `greedy_pig`, `prisoners_dilemma`, `lineup4`, `arena_champions`
- `database/` — SQLModel ORM models (`db_models.py`), DB config (`db_config.py`), session management, `init_db.py` for schema setup
- `migrations/` — dated SQL migrations for production schema changes (not used by tests)
- `celery_app.py` — Celery app: broker config, queue routing, worker settings
- `Dockerfile` — shared image for api/workers/test-runner (build context is repo root)
- `config.py` — Central config: dynamic game discovery (`GAMES`), league expiry settings, Stripe keys, secrets

Python dependencies are managed with uv (`pyproject.toml` / `uv.lock`), Python 3.14.

### Frontend structure (`frontend/src/`)
- Vite + React 19. Monaco Editor for the in-browser code editor, Material-UI (v7) for components, Tailwind (v4) for utilities
- `AgentGames/` — Main feature area, organized by role: `Admin/`, `User/`, `Institution/`, `Shared/`, `Feedback/`, `Support/`
- `slices/` — Redux Toolkit slices: auth, feedback, games, leagues, rankings, settings, support, teams
- `components/` — Shared UI components

### Auth model
Three user roles: **Admin**, **Team** (student user), **Institution** (manages teams/leagues; subscriptions billed via Stripe). JWT tokens with role-based route guards. Demo users get short-lived tokens.

### Game framework
Each game extends `BaseGame` and implements match logic. `GameFactory` resolves game classes by folder-name convention at runtime. Games produce structured feedback (Markdown + JSON) shown in the frontend. `backend/games/game_instructions.md` documents how to add a new game.

### Testing
- Tests run inside a Docker container via `docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm test-runner`
- Integration tests hit a real test database (`agent_games_test`) on the same Postgres instance — do not mock the database
- Task-level tests enqueue to the real broker and real workers (never `task_always_eager` — time limits and process isolation don't fire eager); use the `celery_workers` fixture to fail fast when workers are down
- `DB_ENVIRONMENT=test` is set automatically in the test-runner container (and on the workers via `docker-compose.test.yml`)
