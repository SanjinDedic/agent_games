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
RUN groupadd -r validatorgroup && useradd -r -g validatorgroup validatoruser

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . /agent_games/

# Ensure readable permissions for non-root user
RUN chmod -R a+rX /agent_games

# Switch to non-root user
USER validatoruser

EXPOSE 8001

# Log to stdout/stderr (captured by Docker logging driver)
CMD ["python", "/agent_games/backend/docker_utils/services/validation_server.py"]
