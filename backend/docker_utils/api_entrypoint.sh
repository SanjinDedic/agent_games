#!/bin/bash
set -e

# Initialize the database
echo "Initializing database..."
python /agent_games/backend/docker_utils/init_db.py

# Start the API server
echo "Starting API server..."
exec uvicorn backend.api:app --host 0.0.0.0 --port 8000