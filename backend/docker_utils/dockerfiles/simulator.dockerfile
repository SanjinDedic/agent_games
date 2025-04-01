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
RUN groupadd -r simgroup && useradd -r -g simgroup simuser

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (from project root)
COPY . /agent_games/

# Create directories and set permissions
RUN mkdir -p /agent_games/backend/docker_utils/services && \
    chmod -R 755 /agent_games && \
    # Explicitly set permissions for the service scripts
    chmod 755 /agent_games/backend/docker_utils/services/validation_server.py /agent_games/backend/docker_utils/services/simulation_server.py

# Switch to non-root user
USER simuser

EXPOSE 8002

# Use the correct path relative to WORKDIR
CMD ["python", "/agent_games/backend/docker_utils/services/simulation_server.py"]