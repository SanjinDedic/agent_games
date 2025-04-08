"""
Configuration settings for Docker containers and services
"""
import os

# Container configurations
CONTAINERS = {
    "validator": {
        "port": "8001:8001",
        "dockerfile": "docker/dockerfiles/validator.dockerfile",
        "name": "validator",
        "service_file": "docker/services/validation_server.py",
    },
    "simulator": {
        "port": "8002:8002",
        "dockerfile": "docker/dockerfiles/simulator.dockerfile",
        "name": "simulator",
        "service_file": "docker/services/simulation_server.py",
    },
}

# Timeouts (in seconds)
DOCKER_BUILD_TIMEOUT = 300  # 5 minutes for building images
DOCKER_START_TIMEOUT = 30  # 30 seconds for starting containers
CONTAINER_READY_DELAY = 2  # 2 seconds wait after container start

# Service URLs - environment aware
if os.environ.get("TESTING") == "1":
    # For tests, use localhost
    VALIDATOR_URL = "http://localhost:8001/validate"
    SIMULATOR_URL = "http://localhost:8002/simulate"
else:
    # For Docker environment
    VALIDATOR_URL = "http://validator:8001/validate"
    SIMULATOR_URL = "http://simulator:8002/simulate"

# Default simulation parameters
DEFAULT_NUM_SIMULATIONS = 100
DEFAULT_TIMEOUT = 40  # seconds

# Volume mount path inside containers
CONTAINER_MOUNT_PATH = "/agent_games/backend"
