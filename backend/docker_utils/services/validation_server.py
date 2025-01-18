import ast
import logging
import sys
from typing import Any, Dict, Optional, Tuple, Union
from datetime import datetime, timedelta

# Add the backend directory to Python path
sys.path.insert(0, "/backend")

from database.db_models import League
from fastapi import FastAPI
from games.game_factory import GameFactory
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('validation_server.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI()

# Security configuration
ALLOWED_MODULES = {
    "random": None,
    "games": None,
    "player": None,
    "math": None,
}

RISKY_FUNCTIONS = [
    "eval", "exec", "open", "compile", "execfile", "input",
    "os", "sys", "subprocess", "importlib", "__import__",
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
            self.error_message = f"Unauthorized import: {node.module}.{node.names[0].name}"
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
    """Get recent log entries"""
    logger.info("Received request for recent logs")
    try:
        with open("validation_server.log", "r") as f:
            logs = f.read()
        return {"logs": logs}
    except FileNotFoundError:
        return {"logs": "No logs found"}


@app.post("/validate", response_model=ValidationResponse)
async def validate_submission(request: ValidationRequest) -> ValidationResponse:
    """Validate submitted code and run test simulation"""
    logger.info(f"Received validation request for team {request.team_name}")
    try:
        # Validate code safety first
        is_safe, error_message = validate_code(request.code)
        if not is_safe:
            return ValidationResponse(
                status="error", 
                message=f"Agent code is not safe: {error_message}"
            )
        
        logger.info(f"Code passed safety tests for team name:{request.team_name}")

        try:
            # Create test league with validation players
            test_league = League(
                name="validation_leagueX",
                created_date=datetime.now(),
                expiry_date=datetime.now() + timedelta(days=1),
                game=request.game_name
            )
            logger.info(f"Test league created for team name:{request.team_name}")

            # Get game class and instantiate it
            game_class = GameFactory.get_game_class(request.game_name)
            game_instance = game_class(test_league)  # Create instance

            logger.info(f"Added validation players")
            logger.info(f"Game instance players: {game_instance.players}")

            # Add the submitted player code
            game_instance.add_player(request.code, request.team_name)
            logger.info(f"Added player to game instance")

            # Run simulations using the instance
            feedback_result = game_instance.run_single_game_with_feedback(
                test_league, 
                request.custom_rewards
            )
            logger.info(f"Feedback result: {feedback_result}")
            
            # Create new game instance for simulations
            sim_game_instance = game_class(test_league)
            sim_game_instance.add_player(request.code, request.team_name)
            simulation_results = sim_game_instance.run_simulations(
                request.num_simulations,
                test_league,
                request.custom_rewards
            )
            logger.info(f"Simulation results: {simulation_results}")

            return ValidationResponse(
                status="success",
                feedback=feedback_result.get("feedback"),
                simulation_results=simulation_results,
            )

        except Exception as e:
            logger.error(f"Simulation error: {str(e)}")
            return ValidationResponse(
                status="error", 
                message=f"Error during simulation: {str(e)}"
            )

    except Exception as e:
        logger.error(f"Unexpected error during validation: {str(e)}")
        return ValidationResponse(
            status="error", 
            message=f"Unexpected error during validation: {str(e)}"
        )
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)