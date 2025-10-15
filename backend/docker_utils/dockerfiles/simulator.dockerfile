# Stage 1: Build stage
FROM python:3.13 AS builder

WORKDIR /build
COPY ./backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.13

WORKDIR /agent_games

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/agent_games

# Install curl for healthchecks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Create non-root user and group
RUN groupadd -r simgroup && useradd -r -g simgroup simuser

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . /agent_games/

# Create logs directory (the file will be mounted from host)
RUN mkdir -p /agent_games/logs && \
    chmod -R 755 /agent_games && \
    chmod 755 /agent_games/backend/docker_utils/services/simulation_server.py

# Switch to non-root user
# USER simuser

EXPOSE 8002

# SECURE: Append to mounted log file (file already exists on host)
CMD ["sh", "-c", "python /agent_games/backend/docker_utils/services/simulation_server.py 2>&1 | tee -a /agent_games/logs/simulator.log"]
