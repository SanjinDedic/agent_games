#!/bin/bash
echo "Setting up secure log files..."

# Stop any running containers first
echo "Stopping Docker containers..."
docker compose down 2>/dev/null || true

# Remove existing logs directory completely to start fresh
if [ -d "./logs" ]; then
    echo "Removing existing logs directory..."
    sudo rm -rf ./logs
fi

# Create logs directory
echo "Creating logs directory..."
mkdir -p ./logs

# Create log files (these will definitely be files now)
echo "Creating log files..."
touch ./logs/api.log
touch ./logs/validator.log
touch ./logs/simulator.log

# Set secure permissions:
# 666 = rw-rw-rw- (read/write for owner, group, others - NO execute)
# This allows containers to append but files can't be executed
chmod 666 ./logs/api.log
chmod 666 ./logs/validator.log
chmod 666 ./logs/simulator.log

echo "Log files created with permissions:"
ls -la ./logs/

echo "Verifying files are actually files (not directories):"
file ./logs/api.log
file ./logs/validator.log  
file ./logs/simulator.log

echo "✅ Log setup complete. Safe to start containers."