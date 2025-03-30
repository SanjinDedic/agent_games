#!/bin/bash

# This script starts the microservices using Docker Compose

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

# Start the services
echo "Starting services with Docker Compose..."
docker-compose up -d

# Check if services started successfully
echo "Checking service status..."
docker-compose ps

echo "Services started. API will be accessible at http://localhost:8000"
echo "Validator service at http://localhost:8001"
echo "Simulator service at http://localhost:8002"