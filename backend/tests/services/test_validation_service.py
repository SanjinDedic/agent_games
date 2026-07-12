import ast

from backend.routes.user.code_validation import CodeValidator, validate_code
from backend.tasks.validation_task import run_validation

# Test constants
VALID_CODE = """
from games.prisoners_dilemma.player import Player
import random
import math

class CustomPlayer(Player):
    def make_decision(self, game_state):
        self.add_feedback("Making a decision")
        return 'collude'
"""

def test_validation_task_custom_rewards(celery_workers):
    """Validation task succeeds with custom rewards (the plain valid-code run
    is covered by test_celery_tasks.test_validation_workflow)"""
    result = run_validation.delay(
        code=VALID_CODE,
        game_name="prisoners_dilemma",
        team_name="test_team",
        custom_rewards=[4, 0, 6, 2],
    ).get(timeout=20)
    assert result["status"] == "success"


def test_validate_code_syntax_error():
    """Invalid syntax is caught by the pre-enqueue AST check"""
    is_safe, message = validate_code("This is not valid Python code")
    assert not is_safe
    assert "syntax error" in message.lower()


def test_validation_task_invalid_game(celery_workers):
    """Test that an invalid game name surfaces as a task error"""
    result = run_validation.delay(
        code=VALID_CODE,
        game_name="invalid_game",
        team_name="test_team",
    ).get(timeout=20)
    assert result["status"] == "error"
    assert "Unknown game" in result["message"]


def test_code_validator_success():
    """Test successful code validation scenarios"""
    validator = CodeValidator()

    # Test case 1: Valid imports
    code = "import random\nimport math"
    tree = ast.parse(code)
    validator.visit(tree)
    assert validator.safe
    assert validator.error_message is None

    # Test case 2: Valid code with allowed functionality
    code = """
from games.prisoners_dilemma.player import Player
class CustomPlayer(Player):
    def make_decision(self, game_state):
        return random.choice(['collude', 'defect'])
"""
    tree = ast.parse(code)
    validator.safe = True  # Reset for new test
    validator.visit(tree)
    assert validator.safe


def test_code_validator_exceptions():
    """Test code validator error cases"""
    validator = CodeValidator()

    # Test case 1: Unauthorized import
    code = "import os"
    tree = ast.parse(code)
    validator.visit(tree)
    assert not validator.safe
    assert "unauthorized import" in validator.error_message.lower()

    # Test case 2: Unauthorized from import
    code = "from os import system"
    tree = ast.parse(code)
    validator.safe = True  # Reset for new test
    validator.visit(tree)
    assert not validator.safe
    assert "unauthorized import" in validator.error_message.lower()

    # Test case 3: Unauthorized function call (eval)
    code = "eval('1 + 1')"
    tree = ast.parse(code)
    validator.safe = True  # Reset for new test
    validator.visit(tree)
    assert not validator.safe
    assert "unauthorized function" in validator.error_message.lower()

    # Test case 4: Unauthorized function call (exec)
    code = "exec('print(\"hello\")')"
    tree = ast.parse(code)
    validator.safe = True  # Reset for new test
    validator.visit(tree)
    assert not validator.safe
    assert "unauthorized function" in validator.error_message.lower()


def test_validation_task_simulation_error(celery_workers):
    """A crashing agent fails validation — no default action is substituted."""
    error_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return 1 / 0  # Will cause ZeroDivisionError
"""
    result = run_validation.delay(
        code=error_code,
        game_name="prisoners_dilemma",
        team_name="test_team",
        num_simulations=10,
    ).get(timeout=20)
    assert result["status"] == "error"
    assert result["message"].startswith("Error during simulation:")
    assert "Invalid decision by test_team" in result["message"]
    assert "ZeroDivisionError" in result["traceback"]


def test_validation_task_player_feedback(celery_workers):
    """Test that player feedback is properly captured"""
    feedback_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        self.add_feedback("Testing feedback mechanism")
        return 'collude'
"""
    result = run_validation.delay(
        code=feedback_code,
        game_name="prisoners_dilemma",
        team_name="test_team",
        num_simulations=10,
    ).get(timeout=20)
    assert result["status"] == "success"
    assert "feedback" in result
    assert isinstance(result["feedback"], (dict, str))
