FROM python:3.13

# Set working directory to agent_games (parent of backend)
WORKDIR /agent_games

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/agent_games

# Create non-root user and group
RUN groupadd -r validatorgroup && useradd -r -g validatorgroup validatoruser

# Install requirements and curl
RUN apt-get update && apt-get install -y curl

# Copy requirements and install dependencies 
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application files
COPY . /agent_games/backend/

# Set ownership of the working directory and all files
RUN chown -R validatoruser:validatorgroup /agent_games

# Switch to non-root user
USER validatoruser

EXPOSE 8001

CMD ["python", "backend/docker_utils/services/validation_server.py"]