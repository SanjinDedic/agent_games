# Stage 1: Build stage
FROM python:3.14-alpine AS builder

WORKDIR /agent_games

# Install uv and build dependencies for compiled packages
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN apk add --no-cache gcc musl-dev postgresql-dev

# Install dependencies including test group (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --group test

# Stage 2: Runtime stage
FROM python:3.14-alpine

# Set working directory
WORKDIR /agent_games

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/agent_games
ENV PATH="/agent_games/.venv/bin:$PATH"
ENV DB_ENVIRONMENT=test

# Install curl for healthchecks, libpq for psycopg, and Docker CLI for tests
RUN apk add --no-cache curl libpq docker-cli

# Copy virtual environment from builder stage
COPY --from=builder /agent_games/.venv /agent_games/.venv

# Copy application code (from project root)
COPY . /agent_games/

# Create directories and set permissions
RUN chmod -R 755 /agent_games

CMD ["pytest", "backend/tests/", "-v"]
