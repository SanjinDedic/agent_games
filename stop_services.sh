#!/bin/bash

echo "🛑 Stopping all running containers..."
docker stop $(docker ps -q)

echo "�� Removing all containers..."
docker rm $(docker ps -aq)

echo "🚫 Disabling auto-restart for all containers..."
docker update --restart=no $(docker ps -aq)

echo "✅ All services stopped and cleaned up."
