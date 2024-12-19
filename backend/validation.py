import ast
import logging
import os
import subprocess
import time

import httpx
from config import ROOT_DIR
from utils import get_games_names

# Set up logging properly
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(ROOT_DIR, "validation.log")),
    ],
)
logger = logging.getLogger(__name__)


class ValidationSimulationError(Exception):
    pass


# List of allowed modules and their allowed sub-modules
# Dynamically generate the ALLOWED_MODULES dictionary
ALLOWED_MODULES = {
    "random": None,  # None means no specific sub-modules are allowed
    "games": {game_name: {"player": None} for game_name in get_games_names()},
    "player": None,  # Allow direct import from player
}

# List of risky functions
RISKY_FUNCTIONS = ["eval", "exec", "open", "compile", "execfile", "input"]


class SafeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.safe = True

    def visit_Import(self, node):
        for alias in node.names:
            if not self.is_allowed_import(alias.name):
                self.safe = False
                return
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if not self.is_allowed_import(node.module, node.names[0].name):
            self.safe = False
            return
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in RISKY_FUNCTIONS:
            self.safe = False
            return
        self.generic_visit(node)

    def is_allowed_import(self, module, submodule=None):
        parts = module.split(".")
        current = ALLOWED_MODULES
        for part in parts:
            if part not in current:
                return False
            if current[part] is None:
                return True
            current = current[part]

        if submodule:
            return submodule in current
        return True


def is_agent_safe(code):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    checker = SafeVisitor()
    checker.visit(tree)
    return checker.safe


class ValidatorContainer:
    def __init__(self):
        self.container_name = "validator"
        self.port = 8001

    def is_running(self):
        """Check if the validator container is running"""
        try:
            result = subprocess.run(
                ["docker", "ps", "-q", "-f", f"name={self.container_name}"],
                capture_output=True,
                text=True,
            )
            return bool(result.stdout.strip())
        except Exception as e:
            logger.error(f"Error checking container status: {e}")
            return False

    def start(self):
        """Start the validator container if it's not running"""
        if not self.is_running():
            try:
                # Check if image exists, build if it doesn't
                result = subprocess.run(
                    ["docker", "images", "-q", "validator"],
                    capture_output=True,
                    text=True,
                )
                if not result.stdout.strip():
                    logger.info("Building validator image...")
                    subprocess.run(
                        [
                            "docker",
                            "build",
                            "-t",
                            "validator",
                            "-f",
                            "validator.dockerfile",
                            ".",
                        ],
                        check=True,
                    )

                # Run the container
                logger.info("Starting validator container...")
                subprocess.run(
                    [
                        "docker",
                        "run",
                        "-d",
                        "--name",
                        self.container_name,
                        "-p",
                        f"{self.port}:8001",
                        "-v",
                        f"{ROOT_DIR}:/agent_games",
                        "--restart",
                        "always",
                        "validator",
                    ],
                    check=True,
                )

                # Wait for container to be ready
                time.sleep(2)  # Give the server a moment to start
                logger.info("Validator container started successfully")

            except subprocess.CalledProcessError as e:
                logger.error(f"Error starting validator container: {e}")
                raise ValidationSimulationError("Failed to start validation service")


async def run_validation_simulation(code, game_name, team_name):
    """Run validation using the validator container"""
    if not is_agent_safe(code):
        raise ValidationSimulationError("Code contains unsafe operations")

    validator = ValidatorContainer()

    try:
        # Ensure validator is running
        validator.start()

        # Send request to validator
        logger.info(f"Sending validation request for team {team_name}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://localhost:{validator.port}/validate",
                json={
                    "code": code,
                    "game_name": game_name,
                    "team_name": team_name,
                    "num_simulations": 100,
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.error(f"Validator service error: {response.text}")
                raise ValidationSimulationError(
                    f"Validator service error: {response.text}"
                )

            result = response.json()
            logger.info(f"Validation completed successfully for team {team_name}")
            return result["feedback"], result["simulation_results"]

    except httpx.HTTPError as e:
        logger.error(f"HTTP error occurred: {e}")
        raise ValidationSimulationError(f"HTTP error occurred: {str(e)}")
    except Exception as e:
        logger.error(f"Validation error: {e}")
        raise ValidationSimulationError(f"Validation error: {str(e)}")
