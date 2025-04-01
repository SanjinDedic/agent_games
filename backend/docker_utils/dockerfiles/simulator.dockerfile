# Stage 1: Build stage
FROM python:3.13 AS builder

WORKDIR /build

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.13

# Set working directory directly to backend
WORKDIR /agent_games/backend

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

# Create directories and set permissions - THIS IS THE NEW CODE
RUN mkdir -p /agent_games/backend/docker_utils/services && \
    chmod -R 755 /agent_games

# Switch to non-root user
USER simuser

EXPOSE 8002

# Use the correct path relative to WORKDIR
CMD ["python", "docker_utils/services/simulation_server.py"]