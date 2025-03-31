#!/bin/bash

# This script starts the microservices using Docker Compose and the main API with uvicorn

# Load environment variables from backend/.env if it exists
if [ -f backend/.env ]; then
    echo "Loading environment variables from backend/.env..."
    export $(grep -v '^#' backend/.env | xargs)
else
    echo "No backend/.env file found."
fi

# Ensure SERVICE_TOKEN is set
if [ -z "$SERVICE_TOKEN" ]; then
    echo "SERVICE_TOKEN is not set. Generating a random one..."
    export SERVICE_TOKEN=$(openssl rand -base64 32)
    echo "SERVICE_TOKEN=$SERVICE_TOKEN" >> backend/.env
fi

# Ensure SECRET_KEY is set
if [ -z "$SECRET_KEY" ]; then
    echo "SECRET_KEY is not set. Generating a random one..."
    export SECRET_KEY=$(openssl rand -base64 32)
    echo "SECRET_KEY=$SECRET_KEY" >> backend/.env
fi

# Check for prerequisites
if ! command -v docker >/dev/null 2>&1; then
    echo "Error: Docker is not installed or not in the PATH"
    exit 1
fi

# Start Docker Compose services
echo "Starting services with Docker Compose..."
if command -v docker compose >/dev/null 2>&1; then
    # Use new docker compose command if available
    if ! docker compose up -d; then
        echo "Error: Failed to start services"
        exit 1
    fi
elif command -v docker-compose >/dev/null 2>&1; then
    # Fall back to docker-compose if needed
    if ! docker-compose up -d; then
        echo "Error: Failed to start services"
        exit 1
    fi
else
    echo "Error: Neither docker compose nor docker-compose is available"
    exit 1
fi

# Check if services started successfully
echo "Checking Docker service status..."
docker ps | grep "agent_games"

# Wait for microservices to be healthy
echo "Waiting for microservices to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    VALIDATOR_READY=$(curl -s http://localhost:8001/health || echo "")
    SIMULATOR_READY=$(curl -s http://localhost:8002/health || echo "")
    
    if [[ "$VALIDATOR_READY" == *"healthy"* ]] && [[ "$SIMULATOR_READY" == *"healthy"* ]]; then
        echo "All microservices are ready!"
        break
    fi
    
    echo "Waiting for microservices to be ready... ($(($RETRY_COUNT+1))/$MAX_RETRIES)"
    RETRY_COUNT=$((RETRY_COUNT+1))
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "Warning: Microservices did not become ready within the timeout period."
    echo "Proceeding with main API startup anyway..."
fi

# Start the main API using uvicorn
echo "Starting main API with uvicorn..."
cd backend

# Set PYTHONPATH to include the project root
export PYTHONPATH="$(dirname $(pwd))"

# Check if we're in a virtual environment
if [ -d "venv" ] && [ -f "venv/bin/uvicorn" ]; then
    echo "Using virtual environment for uvicorn..."
    # If the script is meant to keep running, don't include the & at the end
    ./venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000
else
    echo "Using system uvicorn..."
    # If the script is meant to keep running, don't include the & at the end
    uvicorn api:app --host 0.0.0.0 --port 8000
fi

# This part will only execute if the uvicorn process exits
echo "Main API process has exited"