import ast
import logging

import pytest
from fastapi.testclient import TestClient

from backend.docker_utils.services.validation_server import (
    CodeValidator,
    app,
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


@pytest.fixture
def validator_client() -> TestClient:
    """Create a test client for the validator service"""
    return TestClient(app, base_url="http://localhost:8001")


def test_health_check_success(validator_client: TestClient):
    """Test health check endpoint"""
    response = validator_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_validate_endpoint_success(validator_client: TestClient):
    """Test successful validation scenarios"""

    # Test case 1: Basic valid code validation
    data = {
        "code": VALID_CODE,
        "game_name": "prisoners_dilemma",
        "team_name": "test_team",
        "num_simulations": 20,
        "custom_rewards": None,
    }
    response = validator_client.post("/validate", json=data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "feedback" in data
    assert "simulation_results" in data

    # Test case 2: Validation with custom rewards
    data = {
        "code": VALID_CODE,
        "game_name": "prisoners_dilemma",
        "team_name": "test_team",
        "num_simulations": 20,
        "custom_rewards": [4, 0, 6, 2],
    }
    response = validator_client.post("/validate", json=data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_validate_endpoint_exceptions(validator_client: TestClient):
    """Test error cases for validation endpoint"""

    # Test case 1: Invalid syntax
    data = {
        "code": "This is not valid Python code",
        "game_name": "prisoners_dilemma",
        "team_name": "test_team",
        "num_simulations": 100,
        "custom_rewards": None,
    }
    response = validator_client.post("/validate", json=data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "syntax error" in data["message"].lower()

    # Test case 2: Unsafe code
    data = {
        "code": UNSAFE_CODE,
        "game_name": "prisoners_dilemma",
        "team_name": "test_team",
        "num_simulations": 20,
        "custom_rewards": None,
    }
    response = validator_client.post("/validate", json=data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "not safe" in data["message"].lower()

    # Test case 3: Invalid game name
    data = {
        "code": VALID_CODE,
        "game_name": "invalid_game",
        "team_name": "test_team",
        "num_simulations": 10,
        "custom_rewards": None,
    }
    response = validator_client.post("/validate", json=data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "Unknown game" in data["message"]


def test_get_logs_success(validator_client: TestClient):
    """Test successful log retrieval"""
    response = validator_client.get("/logs")
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data


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


def test_validate_endpoint_simulation_error(validator_client: TestClient):
    """Test handling of simulation errors"""
    error_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return 1 / 0  # Will cause ZeroDivisionError
"""
    data = {
        "code": error_code,
        "game_name": "prisoners_dilemma",
        "team_name": "test_team",
        "num_simulations": 10,
        "custom_rewards": None,
    }
    response = validator_client.post("/validate", json=data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["simulation_results"]["table"]["defections"]["test_team"] == 0


def test_validate_endpoint_player_feedback(validator_client: TestClient):
    """Test that player feedback is properly captured"""
    feedback_code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        self.add_feedback("Testing feedback mechanism")
        return 'collude'
"""
    data = {
        "code": feedback_code,
        "game_name": "prisoners_dilemma",
        "team_name": "test_team",
        "num_simulations": 10,
        "custom_rewards": None,
    }
    response = validator_client.post("/validate", json=data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "feedback" in data
    assert isinstance(data["feedback"], (dict, str))
