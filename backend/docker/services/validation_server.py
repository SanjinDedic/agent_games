import ast
import logging
import os
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, Union

# Add the root directory to Python path
sys.path.append("/agent_games")

from fastapi import FastAPI
from games.game_factory import GameFactory

# Now we can import our local modules
from models_db import League
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=4)

# Security configuration
ALLOWED_MODULES = {
    "random": None,
    "games": None,
    "player": None,
    "math": None,
}

RISKY_FUNCTIONS = [
    "eval",
    "exec",
    "open",
    "compile",
    "execfile",
    "input",
    "os",
    "sys",
    "subprocess",
    "importlib",
    "__import__",
]


class ValidationRequest(BaseModel):
    code: str
    game_name: str
    team_name: str
    num_simulations: int = 100
    custom_rewards: Optional[list] = None


class ValidationResponse(BaseModel):
    status: str
    message: Optional[str] = None
    feedback: Union[str, Dict, None] = None
    simulation_results: Optional[Dict[str, Any]] = None


class CodeValidator(ast.NodeVisitor):
    """AST visitor for validating code safety"""

    def __init__(self):
        self.safe = True
        self.error_message = None

    def visit_Import(self, node):
        for alias in node.names:
            if not self._is_allowed_import(alias.name):
                self.safe = False
                self.error_message = f"Unauthorized import: {alias.name}"
                return
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if not self._is_allowed_import(node.module, node.names[0].name):
            self.safe = False
            self.error_message = (
                f"Unauthorized import: {node.module}.{node.names[0].name}"
            )
            return
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in RISKY_FUNCTIONS:
            self.safe = False
            self.error_message = f"Unauthorized function call: {node.func.id}"
            return
        self.generic_visit(node)

    def _is_allowed_import(self, module: str, submodule: str = None) -> bool:
        parts = module.split(".")
        current = ALLOWED_MODULES

        for part in parts:
            if part not in current:
                return False
            if current[part] is None:
                return True
            current = current[part]

        return submodule in current if submodule else True


def validate_code(code: str) -> Tuple[bool, Optional[str]]:
    """Validate code safety using AST analysis"""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error in code: {str(e)}"

    validator = CodeValidator()
    validator.visit(tree)
    return validator.safe, validator.error_message


def setup_test_environment(
    code: str, team_name: str, game_name: str
) -> Tuple[str, str]:
    """Set up temporary test environment"""
    temp_dir = tempfile.mkdtemp()
    temp_league_path = os.path.join(temp_dir, "test_league")
    os.makedirs(temp_league_path)

    # Copy test league bots
    test_league_path = os.path.join(
        "/agent_games/games", game_name, "leagues/test_league"
    )
    if os.path.exists(test_league_path):
        for item in os.listdir(test_league_path):
            if item.endswith(".py"):
                shutil.copy2(
                    os.path.join(test_league_path, item),
                    os.path.join(temp_league_path, item),
                )

    # Write submitted code
    with open(os.path.join(temp_league_path, f"{team_name}.py"), "w") as f:
        f.write(code)

    return temp_league_path, temp_dir


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/validate", response_model=ValidationResponse)
async def validate_submission(request: ValidationRequest) -> ValidationResponse:
    """Validate submitted code and run test simulation"""
    try:
        # Validate code safety first
        is_safe, error_message = validate_code(request.code)
        if not is_safe:
            return ValidationResponse(
                status="error", message=f"Agent code is not safe: {error_message}"
            )

        # Set up test environment
        temp_league_path, temp_dir = setup_test_environment(
            request.code, request.team_name, request.game_name
        )

        try:
            test_league = League(
                name="test_league",
                created_date=datetime.now(),
                expiry_date=datetime.now() + timedelta(days=1),
                folder=temp_league_path,
                game=request.game_name,
            )

            # Get game class and run simulations
            game_class = GameFactory.get_game_class(request.game_name)

            # Run simulations within a timeout context
            feedback_result = game_class.run_single_game_with_feedback(
                test_league, request.custom_rewards
            )
            simulation_results = game_class.run_simulations(
                request.num_simulations, test_league, request.custom_rewards
            )

            return ValidationResponse(
                status="success",
                feedback=feedback_result.get("feedback"),
                simulation_results=simulation_results,
            )

        except Exception as e:
            logger.error(f"Simulation error: {str(e)}")
            return ValidationResponse(
                status="error", message=f"Error during simulation: {str(e)}"
            )

        finally:
            # Clean up temporary files
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.error(f"Error cleaning up temporary directory: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error during validation: {str(e)}")
        return ValidationResponse(
            status="error", message=f"Unexpected error during validation: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
