# Stage 1: Build stage
FROM python:3.14-alpine AS builder

WORKDIR /agent_games

# Install uv and build dependencies for compiled packages
RUN pip install --no-cache-dir uv
RUN apk add --no-cache gcc musl-dev postgresql-dev

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock ./
ARG BUILD_ENV=production
RUN if [ "$BUILD_ENV" = "test" ]; then \
      uv sync --frozen --no-install-project --group test; \
    else \
      uv sync --frozen --no-install-project --no-dev; \
    fi

# Stage 2: Runtime stage
FROM python:3.14-alpine

WORKDIR /agent_games

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/agent_games
ENV PATH="/agent_games/.venv/bin:$PATH"

# Copy libpq from builder — no apk add needed for psycopg
COPY --from=builder /usr/lib/libpq.so* /usr/lib/

# Only install extra packages when needed (e.g. postgresql18-client for api, docker-cli for test-runner)
ARG RUNTIME_PACKAGES=""
RUN if [ -n "$RUNTIME_PACKAGES" ]; then apk add --no-cache $RUNTIME_PACKAGES; fi

# Create non-root user and group
RUN addgroup -S apigroup && adduser -S apiuser -G apigroup

# Copy virtual environment from builder stage
COPY --from=builder /agent_games/.venv /agent_games/.venv

# Copy application code (from project root)
COPY . /agent_games/

# Create directories and set permissions
RUN chmod -R 755 /agent_games

# Switch to non-root user
# USER apiuser

EXPOSE 8000

# backend/entrypoint.sh runs the one-shot pre-start (schema init/seed + idempotent
# SQL migrations), then execs the server — production gunicorn by default, or
# whatever is passed as arguments (dev compose passes uvicorn --reload). Kept out
# of the app lifespan: every gunicorn worker runs the lifespan, so init there races.
CMD ["sh", "backend/entrypoint.sh"]
