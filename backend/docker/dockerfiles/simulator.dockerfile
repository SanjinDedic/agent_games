FROM python:3.12

WORKDIR /agent_games

ENV PYTHONDONTWRITEBYTRACE=1
ENV PYTHONUNBUFFERED=1

# Install requirements and curl
RUN apt-get update && apt-get install -y curl

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application files
COPY . /agent_games/

# Debug: List contents to verify files
RUN ls -la /agent_games/
RUN ls -la /agent_games/docker/services/

# Expose port
EXPOSE 8002

# Run the server directly from its location
CMD ["python", "docker/services/simulation_server.py"]