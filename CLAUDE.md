# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running tests
Tests run locally via pytest but require Docker Compose services running. One-time local setup:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
pip install pytest pytest-asyncio httpx pytest-cov
```

```bash
# 1. Start services with test profile (spins up api, validator, simulator, postgres_test)
docker compose --profile test up -d

# 2. Run tests (from repo root, with test env vars)
DB_ENVIRONMENT=test DATABASE_URL="postgresql+psycopg://postgres:test_db_password@localhost:5433/agent_games_test" pytest backend/tests/

# Run a single test file
DB_ENVIRONMENT=test DATABASE_URL="postgresql+psycopg://postgres:test_db_password@localhost:5433/agent_games_test" pytest backend/tests/integration/routes/auth/test_auth.py -v

# Run with coverage
DB_ENVIRONMENT=test DATABASE_URL="postgresql+psycopg://postgres:test_db_password@localhost:5433/agent_games_test" pytest --cov=backend --cov-report=term backend/tests/
```

### Running the app
```bash
# Development (includes frontend + postgres)
docker compose --profile dev up -d

# First-time DB init
docker compose exec api python -m backend.docker_utils.init_db

./stop_services.sh   # Stop all containers
./setup_logs.sh      # One-time log setup before first run
```

### Frontend (standalone)
```bash
cd frontend
npm install
npm start        # Dev server on port 3000
npm run build    # Production build
```

## Architecture

This is a **multi-game agent simulation platform** where students/teams submit code agents that compete in game simulations.

### Services (docker compose)
- **API** (port 8000): Main FastAPI app — authentication, league/team management, agent submission
- **Validator** (port 8001): Validates submitted agent code before acceptance
- **Simulator** (port 8002): Executes game simulations in isolated Docker containers
- **PostgreSQL** (port 5432): Main DB; test DB on port 5433
- **Frontend** (port 3000): React SPA

The API calls Validator and Simulator via async HTTP (httpx/aiohttp). Simulator runs submitted code in isolated Docker containers with resource limits (500MB RAM, 50 processes).

### Backend structure (`backend/`)
- `api.py` — FastAPI app entry point, mounts all routers
- `routes/` — Route modules grouped by domain: `admin/`, `agent/`, `auth/`, `demo/`, `diagnostics/`, `institution/`, `user/`
- `games/` — Game implementations extending `base_game.py`. Games: `greedy_pig`, `prisoners_dilemma`, `lineup4`, `arena_champions`. New games are registered in `game_factory.py`
- `database/` — SQLModel ORM models (`db_models.py`), DB config (`db_config.py`), session management
- `docker_utils/` — Docker SDK integration for container execution; `init_db.py` for schema setup
- `config.py` — Central config: service URLs, game list, league expiry settings, secrets

### Frontend structure (`frontend/src/`)
- `AgentGames/` — Main feature area, organized by role: `Admin/`, `User/`, `Institution/`, `Shared/`, `Feedback/`
- `slices/` — Redux Toolkit slices (leagues, teams, agents, feedback)
- `components/` — Shared UI components
- Uses Monaco Editor for the in-browser code editor, Material-UI for components, Tailwind for utilities

### Auth model
Three user roles: **Admin**, **Team** (student user), **Institution** (manages teams/leagues). JWT tokens with role-based route guards. Demo users get short-lived tokens.

### Game framework
Each game extends `BaseGame` and implements match logic. The `game_factory.py` registers available games. Games produce structured feedback (Markdown + JSON) shown in the frontend. `backend/games/game_instructions.md` documents how to add a new game.

### Testing
- Integration tests hit a real test PostgreSQL instance (port 5433) — do not mock the database
- Test environment is configured in `backend/tests/conftest.py` via `setup_test_environment` fixture
- `DB_ENVIRONMENT=test` env var switches the DB connection to the test database
