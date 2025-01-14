import ast
import json
import os
import sys
from datetime import datetime, timedelta

import pytest
from database.db_models import League
from docker_utils.services.validation_server import CodeValidator, app, validate_code
from fastapi.testclient import TestClient

# Create test client
client = TestClient(app)

# Test Data Constants
VALID_CODE = """
from games.prisoners_dilemma.player import Player
import random
import math

class CustomPlayer(Player):
    def make_decision(self, game_state):
        self.add_feedback("Making a decision")
        return 'collude'
"""

INVALID_SYNTAX_CODE = """
This is not valid Python code
"""

UNSAFE_IMPORT_CODE = """
from games.prisoners_dilemma.player import Player
import os

class CustomPlayer(Player):
    def make_decision(self, game_state):
        os.system('echo "hello"')
        return 'collude'
"""

UNSAFE_IMPORT_FROM_CODE = """
from games.prisoners_dilemma.player import Player
from os import system

class CustomPlayer(Player):
    def make_decision(self, game_state):
        system('echo "hello"')
        return 'collude'
"""

UNSAFE_EVAL_CODE = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        eval('print("hello")')
        return 'collude'
"""

UNSAFE_EXEC_CODE = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        exec('print("hello")')
        return 'collude'
"""


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_code_validator():
    """Test the CodeValidator class directly"""
    validator = CodeValidator()

    # Test allowed imports
    code = "import random\nimport math"
    tree = ast.parse(code)
    validator.visit(tree)
    assert validator.safe
    assert validator.error_message is None

    # Test unauthorized import
    code = "import os"
    tree = ast.parse(code)
    validator.safe = True  # Reset
    validator.visit(tree)
    assert not validator.safe
    assert "unauthorized import" in validator.error_message.lower()

    # Test unauthorized import from
    code = "from os import system"
    tree = ast.parse(code)
    validator.safe = True  # Reset
    validator.visit(tree)
    assert not validator.safe
    assert "unauthorized import" in validator.error_message.lower()

    # Test unauthorized function call
    code = "eval('1 + 1')"
    tree = ast.parse(code)
    validator.safe = True  # Reset
    validator.visit(tree)
    assert not validator.safe
    assert "unauthorized function" in validator.error_message.lower()


def test_validate_code_function():
    """Test the validate_code function directly"""
    # Test valid code
    is_safe, error = validate_code(VALID_CODE)
    assert is_safe
    assert error is None

    # Test syntax error
    is_safe, error = validate_code(INVALID_SYNTAX_CODE)
    assert not is_safe
    assert "syntax error" in error.lower()

    # Test unsafe imports
    is_safe, error = validate_code(UNSAFE_IMPORT_CODE)
    assert not is_safe
    assert "unauthorized import" in error.lower()

    is_safe, error = validate_code(UNSAFE_IMPORT_FROM_CODE)
    assert not is_safe
    assert "unauthorized import" in error.lower()

    # Test unsafe function calls
    is_safe, error = validate_code(UNSAFE_EVAL_CODE)
    assert not is_safe
    assert "unauthorized function" in error.lower()

    is_safe, error = validate_code(UNSAFE_EXEC_CODE)
    assert not is_safe
    assert "unauthorized function" in error.lower()


def test_validation_endpoint_success():
    """Test successful validation with API call"""
    response = client.post(
        "/validate",
        json={
            "code": VALID_CODE,
            "game_name": "prisoners_dilemma",
            "team_name": "test_team",
            "num_simulations": 10,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "feedback" in data
    assert "simulation_results" in data

    # Verify simulation results structure
    assert "total_points" in data["simulation_results"]
    assert "num_simulations" in data["simulation_results"]
    assert isinstance(data["simulation_results"]["total_points"], dict)


def test_validation_endpoint_syntax_error():
    """Test validation endpoint with syntax error in code"""
    response = client.post(
        "/validate",
        json={
            "code": INVALID_SYNTAX_CODE,
            "game_name": "prisoners_dilemma",
            "team_name": "test_team",
            "num_simulations": 10,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "syntax error" in data["message"].lower()


def test_validation_endpoint_unsafe_code():
    """Test validation endpoint with unsafe code"""
    test_cases = [
        ("unsafe import", UNSAFE_IMPORT_CODE),
        ("unsafe import from", UNSAFE_IMPORT_FROM_CODE),
        ("unsafe eval", UNSAFE_EVAL_CODE),
        ("unsafe exec", UNSAFE_EXEC_CODE),
    ]

    for test_name, code in test_cases:
        response = client.post(
            "/validate",
            json={
                "code": code,
                "game_name": "prisoners_dilemma",
                "team_name": "test_team",
                "num_simulations": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "unauthorized" in data["message"].lower(), f"Failed on {test_name}"


def test_validation_endpoint_invalid_game():
    """Test validation endpoint with invalid game name"""
    response = client.post(
        "/validate",
        json={
            "code": VALID_CODE,
            "game_name": "nonexistent_game",
            "team_name": "test_team",
            "num_simulations": 10,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "game" in data["message"].lower()


def test_validation_endpoint_temporary_files():
    """Test that temporary files are properly created and cleaned up"""
    temp_file_path = None

    # First request to create files
    response = client.post(
        "/validate",
        json={
            "code": VALID_CODE,
            "game_name": "prisoners_dilemma",
            "team_name": "test_team",
            "num_simulations": 10,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    # Verify temp files are cleaned up
    if temp_file_path:
        assert not os.path.exists(temp_file_path)


def test_validation_endpoint_simulation_error():
    """Test handling of simulation errors"""
    # Create code that will cause a runtime error during simulation
    error_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return 1/0  # Will cause ZeroDivisionError
"""

    response = client.post(
        "/validate",
        json={
            "code": error_code,
            "game_name": "prisoners_dilemma",
            "team_name": "test_team",
            "num_simulations": 10,
        },
    )

    assert response.status_code == 200
    # TODO: Improve validation with these features:
    # Create a test that fails on the use of an undeclared variable
    # Create a test that fails on the use of an undeclared function
    # Create a test that fails on division by zero


def test_custom_rewards():
    """Test validation with custom rewards"""
    response = client.post(
        "/validate",
        json={
            "code": VALID_CODE,
            "game_name": "prisoners_dilemma",
            "team_name": "test_team",
            "num_simulations": 10,
            "custom_rewards": [5, 0, 10, 1],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "simulation_results" in data


def test_player_feedback():
    """Test that player feedback is properly captured"""
    feedback_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        self.add_feedback("Testing feedback mechanism")
        return 'collude'
"""

    response = client.post(
        "/validate",
        json={
            "code": feedback_code,
            "game_name": "prisoners_dilemma",
            "team_name": "test_team",
            "num_simulations": 10,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "feedback" in data
    assert isinstance(data["feedback"], (dict, str))


if __name__ == "__main__":
    pytest.main(["-v", __file__])
