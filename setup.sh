!/bin/bash

# Check if Docker is installed
if ! [ -x "$(command -v docker)" ]; then
  echo "Docker is not installed. Installing Docker..."

  sudo apt-get remove docker docker-engine docker.io
  sudo apt install docker.io
  sudo snap install docker
  sudo usermod -aG docker $USER
  newgrp docker
fi

docker build -t run-with-docker .

docker stop simulation_container || true
docker rm -f simulation_container || true

docker run -d --name simulation_container run-with-docker