#!/bin/bash

# Ensure environment variables are set
if [ ! -f backend/.env ] || ! grep -q "SERVICE_TOKEN" backend/.env || ! grep -q "SECRET_KEY" backend/.env; then
    echo "Setting up environment tokens..."
    # Generate tokens if needed
    [ -f backend/.env ] || touch backend/.env
    grep -q "SERVICE_TOKEN" backend/.env || echo "SERVICE_TOKEN=$(openssl rand -base64 32)" >> backend/.env
    grep -q "SECRET_KEY" backend/.env || echo "SECRET_KEY=$(openssl rand -base64 32)" >> backend/.env
fi

# Load environment variables
export $(grep -v '^#' backend/.env | xargs)

# Start services
echo "Starting services..."
docker compose up -d

# Start the API
echo "Starting API..."
cd backend && uvicorn api:app --host 0.0.0.0 --port 8000