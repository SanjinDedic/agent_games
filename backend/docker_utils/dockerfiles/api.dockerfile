# Stage 1: Build stage
FROM python:3.13 AS builder

WORKDIR /build

# Copy requirements and install dependencies
COPY ./backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.13

# Install Docker CLI and tools needed for entrypoint script (stat, getent, etc)
RUN apt-get update && \
    apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release coreutils && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y docker-ce-cli && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

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

# Make the entrypoint script executable
COPY ./backend/docker_utils/api_entrypoint.sh /agent_games/entrypoint.sh
RUN chmod +x /agent_games/entrypoint.sh

# Important: We're not setting the USER here because the entrypoint 
# needs to run as root initially to update groups and permissions
# We'll switch to apiuser at the end of the entrypoint script

EXPOSE 8000

# Use entrypoint script to initialize database and start API
ENTRYPOINT ["/agent_games/entrypoint.sh"]