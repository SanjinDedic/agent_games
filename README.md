# Agent Games

A multi-game agent simulation platform where students and teams submit code agents that compete in game simulations.

## Frontend

![React](https://img.shields.io/badge/React-19.2.4-61DAFB?logo=react&logoColor=white)
![Redux](https://img.shields.io/badge/Redux-9.2.0-764ABC?logo=redux&logoColor=white)
![React Router](https://img.shields.io/badge/React_Router-7.13.2-CA4245?logo=react-router&logoColor=white)
![Monaco Editor](https://img.shields.io/badge/Monaco_Editor-4.7.0-00B3E6?logo=visual-studio-code&logoColor=white)

## Backend

![Python](https://img.shields.io/badge/python-3.14-blue.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135.2-009688.svg?logo=fastapi)
![Pydantic](https://img.shields.io/badge/Pydantic-2.12.5-E92063.svg?logo=pydantic)
![SQLModel](https://img.shields.io/badge/SQLModel-0.0.37-3776AB.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-4169E1.svg?logo=postgresql&logoColor=white)
![Gunicorn](https://img.shields.io/badge/Gunicorn-25.3.0-499848.svg?logo=gunicorn&logoColor=white)
![uv](https://img.shields.io/badge/uv-package_manager-DE5FE9.svg?logo=uv&logoColor=white)
[![Tests](https://github.com/SanjinDedic/agent_games/actions/workflows/tests_coverage_deploy.yml/badge.svg)](https://github.com/SanjinDedic/agent_games/actions/workflows/tests_coverage_deploy.yml)
[![codecov](https://codecov.io/gh/SanjinDedic/agent_games/graph/badge.svg?token=PWUU4GJSOD)](https://codecov.io/gh/SanjinDedic/agent_games)

## Containers

All Python services use lightweight two-stage Alpine builds. Dependencies are compiled in a builder stage and only the virtual environment is copied into the final image, keeping containers at ~400MB (API) compared to ~1.6GB for the full Debian-based Python image.

![Docker](https://img.shields.io/badge/Alpine_API-~400MB-0db7ed.svg?logo=docker&logoColor=white)
![Docker](https://img.shields.io/badge/Alpine_Test_Runner-~456MB-0db7ed.svg?logo=docker&logoColor=white)

## Setup

Prerequisites: [Docker](https://docs.docker.com/get-docker/)

```bash
git clone https://github.com/SanjinDedic/agent_games.git
cd agent_games
docker compose up --build
```

That's it. The `.env` file ships with safe local defaults — no configuration needed.

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

The database initializes automatically on first startup.

## Running Tests

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm test-runner
```

## Production

For production, override the `.env` values with real credentials:

```env
POSTGRES_PASSWORD=<real password>
SECRET_KEY=<real secret>
DATABASE_URL=postgresql+psycopg://postgres:<real password>@postgres:5432/agent_games
```

Remove the `command:` line from the `api` service in `docker-compose.yml` to switch from dev uvicorn to gunicorn with 3 workers.

## Service Management

```bash
docker compose logs -f api     # View logs
docker compose down            # Stop all services
docker compose down -v         # Stop and delete database data
```
