#!/bin/bash
set -e

# Dynamic Docker GID handling
if [ -e /var/run/docker.sock ]; then
    # Get GID of the docker socket
    DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)
    echo "Docker socket GID: $DOCKER_GID"
    
    # Create docker group with the right GID or update existing
    if getent group docker_external > /dev/null; then
        # Group exists, update its GID
        groupmod -g $DOCKER_GID docker_external
    else
        # Create new group with correct GID
        groupadd -g $DOCKER_GID docker_external
    fi
    
    # Add our user to this group
    usermod -aG docker_external apiuser
    
    echo "Updated docker_external group to GID: $DOCKER_GID"
fi

# Initialize the database
echo "Initializing database..."
python /agent_games/backend/docker_utils/init_db.py

# Start the API server as apiuser
echo "Starting API server..."
exec su -c "uvicorn backend.api:app --host 0.0.0.0 --port 8000" apiuser