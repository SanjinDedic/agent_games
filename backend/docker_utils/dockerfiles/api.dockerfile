# Stage 1: Build stage
FROM python:3.13 AS builder

WORKDIR /build

# Copy requirements and install dependencies
COPY ./backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.13

# Set working directory
WORKDIR /agent_games

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/agent_games

# Install curl for healthchecks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create non-root user and group
RUN groupadd -r apigroup && useradd -r -g apigroup apiuser

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (from project root)
COPY . /agent_games/

# Create directories and set permissions
RUN chmod -R 755 /agent_games

# Switch to non-root user
USER apiuser

EXPOSE 8000

# Start API server directly with logging (no su needed since we're already apiuser)
CMD ["sh", "-c", "uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload >> /agent_games/logs/api.log 2>&1"]