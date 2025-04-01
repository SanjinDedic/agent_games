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


# Set PYTHONPATH correctly - this script should be run from the agent_games directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH=$SCRIPT_DIR:$PYTHONPATH
echo "Set PYTHONPATH to: $PYTHONPATH"

# Start services
echo "Starting services..."
docker compose up -d

# Start the API
cd ..
pm2 restart ecosystem.config.js