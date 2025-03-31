import ast
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple, Union

from fastapi import FastAPI
from pydantic import BaseModel

from backend.database.db_models import League
from backend.games.game_factory import GameFactory

# Configure logging to use console only
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],  # Only use StreamHandler for console output
)

logger = logging.getLogger(__name__)

app = FastAPI()

# Security configuration
ALLOWED_MODULES = {
    "random": None,
    "string": None,
    "math": None,
    "games": None,
    "player": None,
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


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/logs")
async def get_logs():
    """Return stub for logs since we're only using console logging"""
    return {"logs": "Logs are being streamed to console only. Check Docker logs."}


@app.post("/validate", response_model=ValidationResponse)
async def validate_submission(request: ValidationRequest) -> ValidationResponse:
    """Validate submitted code and run test simulation"""
    logger.info(f"Received validation request for team {request.team_name}")
    try:
        # Code validation remains the same
        is_safe, error_message = validate_code(request.code)
        if not is_safe:
            return ValidationResponse(
                status="error", message=f"Agent code is not safe: {error_message}"
            )

        test_league = League(
            name="validation_leagueX",
            created_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=1),
            game=request.game_name,
        )

        try:
            game_class = GameFactory.get_game_class(request.game_name)
            game_instance = game_class(test_league)
        except Exception as e:
            logger.error(f"Error creating game instance: {str(e)}")
            return ValidationResponse(
                status="error", message=f"Error initializing game: {str(e)}"
            )

        try:
            player = game_instance.add_player(request.code, request.team_name)
            if player is None:
                logger.error(f"Failed to add player for team {request.team_name}")
                return ValidationResponse(
                    status="error",
                    message=f"Failed to create player for team {request.team_name}",
                )
        except Exception as e:
            logger.error(f"Error adding player: {str(e)}")
            return ValidationResponse(
                status="error", message=f"Error adding player: {str(e)}"
            )

        try:
            # Run in thread pool with timeout
            async with asyncio.timeout(15):
                feedback_result = await asyncio.to_thread(
                    game_instance.run_single_game_with_feedback, request.custom_rewards
                )
                await asyncio.to_thread(game_instance.reset)
                simulation_results = await asyncio.to_thread(
                    game_instance.run_simulations,
                    request.num_simulations,
                    test_league,
                    request.custom_rewards,
                )
        except TimeoutError:
            return ValidationResponse(
                status="error",
                message="Operation timed out - agent may be too slow or stuck in a loop",
            )
        except Exception as e:
            logger.error(f"Error during simulation: {str(e)}")
            return ValidationResponse(
                status="error", message=f"Error during simulation: {str(e)}"
            )

        return ValidationResponse(
            status="success",
            feedback=feedback_result.get("feedback"),
            simulation_results=simulation_results,
        )

    except Exception as e:
        logger.error(f"Unexpected error during validation: {str(e)}")
        return ValidationResponse(
            status="error", message=f"Unexpected error during validation: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
