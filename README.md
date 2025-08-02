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

![Python](https://img.shields.io/badge/python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi)
![Pydantic](https://img.shields.io/badge/Pydantic-2.14.5-E92063.svg?logo=pydantic)
![SQLModel](https://img.shields.io/badge/SQLModel-0.0.18-3776AB.svg?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAADASURBVHgBrVMLDcMgEL0yABNlJmACJmBiTMAETMBEwERMgAkmYMIc0KR3FFI+veSSkst731340aqq0qRuDl5k6WjRGONwzNh1eTgHGwqGctDudf6gtfaVS14QzP2HE1+w8M1UBHFhENiNOcBXnOEBxA5QpgT8aqxRkUcgiNNRPwiaLYQcHaQCc9Zn1HYVDeQMW/qpf3ifELiuXBuuGBYBHGTeHvJwwZSDeaA2kTHzRhAIcgH5b+6xgvrLGPq3F0kVB6vV2WVYY7lLAAAAAElFTkSuQmCC)
![Docker](https://img.shields.io/badge/Docker-20.10.21-2496ED.svg?logo=docker&logoColor=white)
![Black](https://img.shields.io/badge/code%20style-black-000000.svg)
[![Tests](https://github.com/SanjinDedic/agent_games/actions/workflows/test.yml/badge.svg)](https://github.com/SanjinDedic/agent_games/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/SanjinDedic/agent_games/graph/badge.svg?token=PWUU4GJSOD)](https://codecov.io/gh/SanjinDedic/agent_games)


The backend is powered by FastAPI, handling game logic, user authentication, and data management. It uses SQLModel for database interactions, Pydantic for data validation, and includes Docker integration for secure code execution and simulations. The system features comprehensive game feedback in both Markdown and structured JSON formats. SQLite is used for data storage.


For more information, check out the [Backend README](./backend/README.md).


## 🚀 Getting Started

### ⚡ One-Command Local Setup (Recommended)
**Run the entire platform locally with a single Docker Compose command - no configuration files needed!**

1. **Clone the repository:**
   ```bash
   git clone https://github.com/SanjinDedic/agent_games.git
   cd agent_games
   ```

2. **Launch everything with one command:**
   ```bash
   docker compose --profile dev up --build
   ```

**That's it!** This single command will:
- ✅ Build and start all services (API, validator, simulator, frontend, database)
- ✅ Set up the PostgreSQL database with proper initialization
- ✅ Start the React frontend on `http://localhost:3000`
- ✅ Start the FastAPI backend on `http://localhost:8000`
- ✅ Automatically handle all dependencies and networking between services
- ✅ **No .env file configuration required for local development!**

### Alternative Setup
For instructions on manual setup or detailed deployment options, please refer to the respective README files in the frontend and backend directories.

## 🐳 Docker Compose Deployment

> **Quick Start:** For the fastest local development setup, see the [Getting Started](#-getting-started) section above for a single-command deployment that requires **no configuration files**.

The following section provides detailed information about Docker Compose deployment options for different environments and advanced configurations.

### Prerequisites

- Docker and Docker Compose installed on your system
- Git (to clone the repository)

### Environment Configuration

**For local development:** No .env file is required! Just use the quick start command above.

**For production deployment:** Create a `.env` file in the project root with the following variables:

```env
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
DB_NAME=agent_games
TEST_DB_NAME=agent_games_test

# Security
SECRET_KEY=your_secure_secret_key

# Frontend Configuration (if building frontend within Docker)
REACT_APP_AGENT_API_URL=http://localhost:8000
```

### Deployment Steps

1. **Clone the repository:**

```bash
git clone https://github.com/yourusername/agent_games.git
cd agent_games
```

2. **Launch the services:**

```bash
# For production deployment
docker-compose --profile prod up -d

# For development deployment (includes test database)
docker-compose --profile dev up -d

# For testing only
docker-compose --profile test up -d
```

This will start the following services:
- API backend (FastAPI) on port 8000
- Validator service on port 8001
- Simulator service on port 8002
- PostgreSQL database on port 5432
- PostgreSQL test database on port 5433 (only in dev and test profiles)

3. **Initialize the database:**

The first time you run the application, you need to initialize the database:

```bash
docker-compose exec api python -m backend.docker_utils.init_db
```

4. **Access the application:**
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Frontend (if deployed separately): http://localhost:3000

### Service Management

```bash
# View logs
docker-compose logs -f

# View logs for a specific service
docker-compose logs -f api

# Stop all services
docker-compose down

# Stop and remove volumes (caution: this will delete database data)
docker-compose down -v
```

### Resource Limits

Each service has memory and process limits configured to ensure stability:
- API: 400MB memory limit, 50 processes
- Validator: 500MB memory limit, 50 processes  
- Simulator: 500MB memory limit, 50 processes
- PostgreSQL: 700MB memory limit

## 💻 Manual Local Development

> **💡 Tip:** For most users, we recommend using the [one-command Docker setup](#-one-command-local-setup-recommended) above instead of manual setup.

For detailed instructions on setting up the backend and frontend manually for local development, please see the [Backend README](./backend/README.md#manual-local-development).

## 📝 Notes

- **Recommended:** Use the single Docker Compose command for the easiest local development experience
- For manual setup: Make sure you have Python, Docker, Node.js, and npm installed on your machine
- Docker is required for running game simulations in secure containers
- The commands for manual setup assume you're using a Unix-based system (Linux or macOS). Windows commands may differ slightly, especially for activating the virtual environment
- The backend server runs on port 8000 by default, and the frontend runs on port 3000
- Use different terminals for running backend and frontend processes when doing manual setup