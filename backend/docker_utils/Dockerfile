# Stage 1: Build stage
FROM python:3.14-alpine AS builder

WORKDIR /agent_games

# Install uv and build dependencies for compiled packages
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
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

# Only install extra packages when needed (e.g. docker-cli for test-runner)
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

CMD ["sh", "-c", "gunicorn backend.api:app --worker-class uvicorn.workers.UvicornWorker --workers ${GUNICORN_WORKERS:-3} --bind 0.0.0.0:8000 --access-logfile - --error-logfile - 2>&1 | tee -a /agent_games/logs/api.log"]
