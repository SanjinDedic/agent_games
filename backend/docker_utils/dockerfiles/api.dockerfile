# Stage 1: Build stage
FROM python:3.14-alpine AS builder

WORKDIR /build

# Install uv and build dependencies for compiled packages
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN apk add --no-cache gcc musl-dev postgresql-dev

# Copy requirements and install dependencies
COPY ./backend/requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt && \
    uv pip install --system --no-cache psycopg[c]

# Stage 2: Runtime stage
FROM python:3.14-alpine

# Set working directory
WORKDIR /agent_games

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/agent_games

# Install curl for healthchecks and libpq for psycopg
RUN apk add --no-cache curl libpq

# Create non-root user and group
RUN addgroup -S apigroup && adduser -S apiuser -G apigroup

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (from project root)
COPY . /agent_games/

# Create directories and set permissions
RUN chmod -R 755 /agent_games

# Switch to non-root user
# USER apiuser

EXPOSE 8000

CMD ["sh", "-c", "gunicorn backend.api:app --worker-class uvicorn.workers.UvicornWorker --workers ${GUNICORN_WORKERS:-3} --bind 0.0.0.0:8000 --access-logfile - --error-logfile - 2>&1 | tee -a /agent_games/logs/api.log"]
