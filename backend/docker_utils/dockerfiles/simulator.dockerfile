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

# Create logs directory and log file, set permissions
RUN mkdir -p /agent_games/logs && \
    touch /agent_games/logs/simulator.log && \
    chmod -R 755 /agent_games && \
    chmod 755 /agent_games/backend/docker_utils/services/simulation_server.py && \
    chown -R simuser:simgroup /agent_games/logs

# Switch to non-root user
USER simuser

EXPOSE 8002

# Start server and redirect logs to file
CMD ["sh", "-c", "python /agent_games/backend/docker_utils/services/simulation_server.py >> /agent_games/logs/simulator.log 2>&1"]