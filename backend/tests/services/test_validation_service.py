import ast

import pytest

from backend.routes.user.code_validation import (
    CodeValidator,
    run_validation,
    validate_code,
)

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

UNSAFE_CODE = """
import os
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        os.system('echo "hello"')
        return 'collude'
"""


def test_validation_task_success(celery_workers):
    """Test successful validation scenarios"""

    # Test case 1: Basic valid code validation
    result = run_validation.delay(
        code=VALID_CODE,
        game_name="prisoners_dilemma",
        team_name="test_team",
        num_simulations=20,
    ).get(timeout=20)
    assert result["status"] == "success"
    assert "feedback" in result
    assert "simulation_results" in result

    # Test case 2: Validation with custom rewards
    result = run_validation.delay(
        code=VALID_CODE,
        game_name="prisoners_dilemma",
        team_name="test_team",
        num_simulations=20,
        custom_rewards=[4, 0, 6, 2],
    ).get(timeout=20)
    assert result["status"] == "success"


def test_validate_code_exceptions():
    """Test error cases caught by the pre-enqueue AST check"""

    # Test case 1: Invalid syntax
    is_safe, message = validate_code("This is not valid Python code")
    assert not is_safe
    assert "syntax error" in message.lower()

    # Test case 2: Unsafe code
    is_safe, message = validate_code(UNSAFE_CODE)
    assert not is_safe
    assert "unauthorized import" in message.lower()


def test_validation_task_invalid_game(celery_workers):
    """Test that an invalid game name surfaces as a task error"""
    result = run_validation.delay(
        code=VALID_CODE,
        game_name="invalid_game",
        team_name="test_team",
        num_simulations=10,
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

    # Test case 3: Unauthorized function call
    code = "eval('1 + 1')"
    tree = ast.parse(code)
    validator.safe = True  # Reset for new test
    validator.visit(tree)
    assert not validator.safe
    assert "unauthorized function" in validator.error_message.lower()


def test_code_validator_unsafe_functions():
    """Test code validator for unsafe function calls"""
    validator = CodeValidator()

    # Test case 1: Unauthorized eval
    code = "eval('1 + 1')"
    tree = ast.parse(code)
    validator.visit(tree)
    assert not validator.safe
    assert "unauthorized function" in validator.error_message.lower()

    # Test case 2: Unauthorized exec
    code = "exec('print(\"hello\")')"
    tree = ast.parse(code)
    validator.safe = True  # Reset for new test
    validator.visit(tree)
    assert not validator.safe
    assert "unauthorized function" in validator.error_message.lower()


def test_validation_task_simulation_error(celery_workers):
    """Test handling of simulation errors"""
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
    assert result["status"] == "success"
    assert result["simulation_results"]["table"]["defections"]["test_team"] == 0


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
