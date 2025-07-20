#!/bin/bash
set -e

# Initialize the database
echo "Initializing database..."
python /agent_games/backend/docker_utils/init_db.py

# Start the API server as apiuser
echo "Starting API server..."
# Use the same pattern as validator and simulator - redirect all output to log file
exec su -c "uvicorn backend.api:app --host 0.0.0.0 --port 8000 --reload" apiuser >> /agent_games/logs/api.log 2>&1