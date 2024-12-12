import ast
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add the project root directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from datetime import datetime, timedelta

from models_db import League
from validation import (ALLOWED_MODULES, RISKY_FUNCTIONS, SafeVisitor,
                        ValidationSimulationError, is_agent_safe,
                        run_validation_simulation)


@pytest.fixture
def test_league():
    return League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        folder="leagues/test_league",
        game="greedy_pig"
    )

def test_is_agent_safe():
    safe_code = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return 'bank' if game_state['unbanked_money'][self.name] > 20 else 'continue'
    """
    assert is_agent_safe(safe_code) == True

    unsafe_code_import = """
import os

class CustomPlayer(Player):
    def make_decision(self, game_state):
        os.system('rm -rf /')
        return 'continue'
    """
    assert is_agent_safe(unsafe_code_import) == False

    unsafe_code_exec = """
class CustomPlayer(Player):
    def make_decision(self, game_state):
        exec('print("Hello, world!")')
        return 'continue'
    """
    assert is_agent_safe(unsafe_code_exec) == False

def test_safe_visitor():
    visitor = SafeVisitor()

    # Test allowed import
    tree = ast.parse("import random")
    visitor.visit(tree)
    assert visitor.safe == True

    # Test disallowed import
    tree = ast.parse("import os")
    visitor.visit(tree)
    assert visitor.safe == False

    # Test allowed import from
    visitor.safe = True
    tree = ast.parse("from games.greedy_pig.player import Player")
    visitor.visit(tree)
    assert visitor.safe == True

    # Test disallowed import from
    visitor.safe = True
    tree = ast.parse("from os import path")
    visitor.visit(tree)
    assert visitor.safe == False

    # Test risky function call
    visitor.safe = True
    tree = ast.parse("eval('1 + 1')")
    visitor.visit(tree)
    assert visitor.safe == False

def test_is_allowed_import():
    visitor = SafeVisitor()

    assert visitor.is_allowed_import("random") == True
    assert visitor.is_allowed_import("os") == False
    assert visitor.is_allowed_import("games.greedy_pig.player") == True
    assert visitor.is_allowed_import("games.greedy_pig.player", "Player") == True
    assert visitor.is_allowed_import("games.unknown_game.player") == False

@patch('validation.run_docker_simulation')
def test_run_validation_simulation(mock_run_docker_simulation, test_league):
    mock_run_docker_simulation.return_value = (True, {
        'feedback': 'Test feedback',
        'player_feedback': 'Test2',
        'simulation_results': {'test': 'results'}
    })

    code = "print('Hello, world!')"
    game_name = "greedy_pig"
    team_name = "test_team"

    feedback, results = run_validation_simulation(code, game_name, team_name)

    assert feedback == 'Test2'
    assert results == {'test': 'results'}

    # Test file creation and deletion
    file_path = os.path.join(project_root, 'games', game_name, 'leagues', 'test_league', f"{team_name}.py")
    assert not os.path.exists(file_path)

@patch('validation.run_docker_simulation')
def test_run_validation_simulation_error(mock_run_docker_simulation, test_league):
    mock_run_docker_simulation.return_value = (False, "Error message")

    code = "print('Hello, world!')"
    game_name = "greedy_pig"
    team_name = "test_team"

    with pytest.raises(ValidationSimulationError, match="Error message"):
        run_validation_simulation(code, game_name, team_name)

def test_allowed_modules():
    assert 'random' in ALLOWED_MODULES
    assert 'games' in ALLOWED_MODULES
    assert 'player' in ALLOWED_MODULES

def test_risky_functions():
    assert 'eval' in RISKY_FUNCTIONS
    assert 'exec' in RISKY_FUNCTIONS
    assert 'open' in RISKY_FUNCTIONS

if __name__ == "__main__":
    pytest.main()