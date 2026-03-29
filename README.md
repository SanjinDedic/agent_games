# Agent Games

This project is a monorepo containing both the frontend and backend for the Agent Games application.

## Frontend

![React](https://img.shields.io/badge/React-18.2.0-61DAFB?logo=react&logoColor=white)
![Redux](https://img.shields.io/badge/Redux-9.1.2-764ABC?logo=redux&logoColor=white)
![React Router](https://img.shields.io/badge/React_Router-6.22.3-CA4245?logo=react-router&logoColor=white)
![Monaco Editor](https://img.shields.io/badge/Monaco_Editor-4.6.0-00B3E6?logo=visual-studio-code&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-Authentication-000000?logo=json-web-tokens&logoColor=white)


The frontend is built with React and Redux, offering a user interface for game submission, league management, and result viewing. It features code editing capabilities and responsive design.

For more details, see the [Frontend README](./frontend/README.md).

## Backend

![Python](https://img.shields.io/badge/python-3.14-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135.2-009688.svg?logo=fastapi)
![Pydantic](https://img.shields.io/badge/Pydantic-2.12.5-E92063.svg?logo=pydantic)
![SQLModel](https://img.shields.io/badge/SQLModel-0.0.37-3776AB.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-4169E1.svg?logo=postgresql&logoColor=white)
![Gunicorn](https://img.shields.io/badge/Gunicorn-25.3.0-499848.svg?logo=gunicorn&logoColor=white)
![Black](https://img.shields.io/badge/code%20style-black-000000.svg)
[![Tests](https://github.com/SanjinDedic/agent_games/actions/workflows/tests_coverage_deploy.yml/badge.svg)](https://github.com/SanjinDedic/agent_games/actions/workflows/tests_coverage_deploy.yml)
[![codecov](https://codecov.io/gh/SanjinDedic/agent_games/graph/badge.svg?token=PWUU4GJSOD)](https://codecov.io/gh/SanjinDedic/agent_games)


The backend is powered by FastAPI, handling game logic, user authentication, and data management. It uses SQLModel for database interactions, Pydantic for data validation, and includes Docker integration for secure code execution and simulations. The system features comprehensive game feedback in both Markdown and structured JSON formats. PostgreSQL is used for data storage. In production, gunicorn with uvicorn workers serves the application.


For more information, check out the [Backend README](./backend/README.md).


## Getting Started

### One-Command Local Setup (Recommended)
**Run the entire platform locally with a single Docker Compose command - no configuration files needed!**

1. **Clone the repository:**
   ```bash
   git clone https://github.com/SanjinDedic/agent_games.git
   cd agent_games
   ```

2. **Launch everything with one command:**
   ```bash
   docker compose up --build
   ```

**That's it!** This single command will:
- Build and start all services (API, validator, simulator, frontend, database)
- Set up the PostgreSQL database with automatic initialization
- Start the React frontend on `http://localhost:3000`
- Start the FastAPI backend on `http://localhost:8000`
- Automatically handle all dependencies and networking between services
- **No .env file configuration required for local development!**

### Alternative Setup
For instructions on manual setup or detailed deployment options, please refer to the respective README files in the frontend and backend directories.

## Docker Compose Deployment

> **Quick Start:** For the fastest local development setup, see the [Getting Started](#one-command-local-setup-recommended) section above for a single-command deployment that requires **no configuration files**.

The following section provides detailed information about Docker Compose deployment options for different environments and advanced configurations.

### Prerequisites

- Docker and Docker Compose installed on your system
- Git (to clone the repository)

### Environment Configuration

**For local development:** No .env file is required! Just use the quick start command above.

**For production deployment:** Create a `.env` file in the project root with the following variables:

```env
# Database Configuration
POSTGRES_PASSWORD=your_secure_password

# Security
SECRET_KEY=your_secure_secret_key

# Gunicorn workers (default: 3, recommended: (2 x CPU cores) + 1)
GUNICORN_WORKERS=3
```

### Deployment Steps

1. **Clone the repository:**

```bash
git clone https://github.com/SanjinDedic/agent_games.git
cd agent_games
```

2. **Launch the services:**

```bash
# For development (uvicorn with hot reload)
docker compose up -d

# For production (uses Dockerfile CMD with gunicorn)
# Remove or comment out the `command:` override in docker-compose.yml
docker compose up -d
```

This will start the following services:
- API backend (FastAPI) on port 8000
- Validator service on port 8001
- Simulator service on port 8002
- PostgreSQL database on port 5432
- Frontend (React) on port 3000

3. **Initialize the database:**

The database is automatically initialized on first startup. To manually reinitialize:

```bash
docker compose exec api python -m backend.docker_utils.init_db
```

4. **Access the application:**
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Frontend: http://localhost:3000

### Running Tests

```bash
# Run all tests
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm test-runner

# Run a single test file
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm test-runner pytest backend/tests/integration/routes/auth/test_auth.py -v

# Run with coverage
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm test-runner pytest --cov=backend --cov-report=term backend/tests/
```

### Service Management

```bash
# View logs
docker compose logs -f

# View logs for a specific service
docker compose logs -f api

# Stop all services
docker compose down

# Stop and remove volumes (caution: this will delete database data)
docker compose down -v
```

### Resource Limits

Each service has memory and process limits configured to ensure stability:
- API: 400MB memory limit, 50 processes
- Validator: 500MB memory limit, 50 processes
- Simulator: 500MB memory limit, 50 processes
- PostgreSQL: 700MB memory limit
- Frontend: 1GB memory limit

## Notes

- **Recommended:** Use the single Docker Compose command for the easiest local development experience
- For manual setup: Make sure you have Python, Docker, Node.js, and npm installed on your machine
- Docker is required for running game simulations in secure containers
- The commands for manual setup assume you're using a Unix-based system (Linux or macOS). Windows commands may differ slightly, especially for activating the virtual environment
- The backend server runs on port 8000 by default, and the frontend runs on port 3000
- Use different terminals for running backend and frontend processes when doing manual setup
