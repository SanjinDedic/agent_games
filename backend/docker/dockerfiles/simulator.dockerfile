FROM python:3.12

WORKDIR /agent_games

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create non-root user and group
RUN groupadd -r simgroup && useradd -r -g simgroup simuser

# Install requirements and curl
RUN apt-get update && apt-get install -y curl

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application files
COPY . /agent_games/

# Set ownership of the working directory
RUN chown -R simuser:simgroup /agent_games

# Switch to non-root user
USER simuser

EXPOSE 8002

CMD ["python", "docker/services/simulation_server.py"]