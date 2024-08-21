#!/bin/bash

# Print a welcome message
echo "Starting setup process..."


# Source or execute the setup_variables.sh script
if [ -f "./setup_variables.sh" ]; then
    echo "Sourcing variables from setup_variables.sh..."
    source ./setup_variables.sh
else
    echo "setup_variables.sh not found. Exiting..."
    exit 1
fi

if [ -f "./configure_python.sh" ]; then
    echo "Running configure_python.sh..."
    ./configure_python.sh
else
    echo "configure_python.sh not found. Skipping..."
fi

if ! [ -x "$(command -v docker)" ]; then
  echo "Docker is not installed. Installing Docker..."

  sudo apt-get remove docker docker-engine docker.io
  sudo apt install docker.io
  sudo snap install docker
  sudo usermod -aG docker $USER
  newgrp docker

fi

echo "Building image with docker..."
docker build -t run-with-docker ..



if [ -f "./configure_service.sh" ]; then
    echo "Running configure_service.sh..."
    ./configure_service.sh
else
    echo "configure_service.sh not found. Skipping..."
fi

if [ -f "./configure_certbot.sh" ]; then
    echo "Running configure_certbot.sh..."
    ./configure_certbot.sh
else
    echo "configure_certbot.sh not found. Skipping..."
fi

if [ -f "./configure_apache.sh" ]; then
    echo "Running configure_apache.sh..."
    ./configure_apache.sh
else
    echo "configure_apache.sh not found. Skipping..."
fi