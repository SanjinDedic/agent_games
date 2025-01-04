import logging
import os
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=4)


class ValidationRequest(BaseModel):
    """Schema for validation request payload"""

    code: str
    game_name: str
    team_name: str
    num_simulations: int = 100
    custom_rewards: Optional[list] = None


class ValidationResponse(BaseModel):
    """Schema for validation response"""

    status: str
    message: Optional[str] = None
    feedback: Optional[Dict[str, Any]] = None
    simulation_results: Optional[Dict[str, Any]] = None


def is_code_safe(code: str) -> bool:
    """
    Check if submitted code contains any unsafe imports or operations
    Simple implementation - for test purposes only
    """
    unsafe_imports = ["os", "sys", "subprocess", "eval", "exec"]
    for unsafe in unsafe_imports:
        if unsafe in code:
            return False
    return True


def run_single_simulation(
    game_class: Any, league: Any, custom_rewards: Optional[list] = None
) -> Dict[str, Any]:
    """Run a single game simulation"""
    game = game_class(league)
    return game.play_game(custom_rewards)


def handle_validation_error(e: Exception, context: str) -> ValidationResponse:
    """Create standardized error response"""
    error_msg = f"{context} error: {str(e)}"
    logger.error(error_msg)
    return ValidationResponse(status="error", message=error_msg)


@app.post("/validate", response_model=ValidationResponse)
def validate_code(request: ValidationRequest) -> ValidationResponse:
    """
    Validate submitted code by:
    1. Checking for unsafe operations
    2. Creating a temporary test environment
    3. Running the code in a controlled simulation
    """
    try:
        # Safety check first
        if not is_code_safe(request.code):
            return ValidationResponse(
                status="error", message="Code contains unsafe operations"
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create temp test league directory
            temp_league_path = os.path.join(temp_dir, "test_league")
            os.makedirs(temp_league_path)

            # Try to copy test league bots if they exist
            test_league_path = os.path.join(
                "/agent_games/games", request.game_name, "leagues/test_league"
            )
            try:
                if os.path.exists(test_league_path):
                    for item in os.listdir(test_league_path):
                        if item.endswith(".py"):
                            src = os.path.join(test_league_path, item)
                            dst = os.path.join(temp_league_path, item)
                            shutil.copy2(src, dst)
            except Exception as e:
                logger.warning(f"Could not copy test bots: {e}")

            # Write submitted code to temp dir
            team_file = os.path.join(temp_league_path, f"{request.team_name}.py")
            with open(team_file, "w") as f:
                f.write(request.code)

            # Create test league instance
            from models_db import League

            test_league = League(
                name="test_league",
                created_date=datetime.now(),
                expiry_date=datetime.now() + timedelta(days=1),
                folder=temp_league_path,
                game=request.game_name,
            )

            try:
                # Import game class dynamically to match request
                from games.game_factory import GameFactory

                game_class = GameFactory.get_game_class(request.game_name)
            except ValueError as e:
                return ValidationResponse(status="error", message=str(e))
            except Exception as e:
                return handle_validation_error(e, "Game class loading")

            # Run validation
            try:
                feedback_result = game_class.run_single_game_with_feedback(
                    test_league, request.custom_rewards
                )

                # Run additional simulations if requested
                simulation_results = run_single_simulation(
                    game_class, test_league, request.custom_rewards
                )

                return ValidationResponse(
                    status="success",
                    feedback=feedback_result.get("feedback"),
                    simulation_results={
                        "total_points": simulation_results.get("points", {}),
                        "num_simulations": 1,
                        "table": simulation_results.get("table", {}),
                    },
                )
            except Exception as e:
                return handle_validation_error(e, "Game simulation")

    except Exception as e:
        return handle_validation_error(e, "Validation")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
