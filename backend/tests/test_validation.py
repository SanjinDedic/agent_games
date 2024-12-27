import ast
import os
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from config import ROOT_DIR
from models_db import League
from validation import (
    ALLOWED_MODULES,
    RISKY_FUNCTIONS,
    SafeVisitor,
    ValidationSimulationError,
    is_agent_safe,
    run_validation_simulation,
)


@pytest.fixture
def test_league():
    return League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        folder="leagues/test_league",
        game="greedy_pig",
    )


def test_is_agent_safe():
    safe_code = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return 'bank' if game_state['unbanked_money'][self.name] > 20 else 'continue'
    """
    assert is_agent_safe(safe_code) is True

    unsafe_code_import = """
import os

class CustomPlayer(Player):
    def make_decision(self, game_state):
        os.system('rm -rf /')
        return 'continue'
    """
    assert is_agent_safe(unsafe_code_import) is False

    unsafe_code_exec = """
class CustomPlayer(Player):
    def make_decision(self, game_state):
        exec('print("Hello, world!")')
        return 'continue'
    """
    assert is_agent_safe(unsafe_code_exec) is False


def test_safe_visitor():
    visitor = SafeVisitor()

    # Test allowed import
    tree = ast.parse("import random")
    visitor.visit(tree)
    assert visitor.safe is True

    # Test disallowed import
    tree = ast.parse("import os")
    visitor.visit(tree)
    assert visitor.safe is False

    # Test allowed import from
    visitor.safe = True
    tree = ast.parse("from games.greedy_pig.player import Player")
    visitor.visit(tree)
    assert visitor.safe is True

    # Test disallowed import from
    visitor.safe = True
    tree = ast.parse("from os import path")
    visitor.visit(tree)
    assert visitor.safe is False

    # Test risky function call
    visitor.safe = True
    tree = ast.parse("eval('1 + 1')")
    visitor.visit(tree)
    assert visitor.safe is False


def test_is_allowed_import():
    visitor = SafeVisitor()

    assert visitor.is_allowed_import("random") is True
    assert visitor.is_allowed_import("os") is False
    assert visitor.is_allowed_import("games.greedy_pig.player") is True
    assert visitor.is_allowed_import("games.greedy_pig.player", "Player") is True
    assert visitor.is_allowed_import("games.unknown_game.player") is False


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_run_validation_simulation(mock_post, test_league):
    mock_response = type(
        "Response",
        (),
        {
            "status_code": 200,
            "json": lambda: {
                "feedback": "Test feedback",
                "simulation_results": {"test": "results"},
            },
            "text": "Success",
        },
    )

    mock_post.return_value = mock_response

    code = "print('Hello, world!')"
    game_name = "greedy_pig"
    team_name = "test_team"

    feedback, results = await run_validation_simulation(code, game_name, team_name)

    assert feedback == "Test feedback"
    assert results == {"test": "results"}


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_run_validation_simulation_error(mock_post, test_league):
    mock_response = type("Response", (), {"status_code": 500, "text": "Error message"})

    mock_post.return_value = mock_response

    code = "print('Hello, world!')"
    game_name = "greedy_pig"
    team_name = "test_team"

    with pytest.raises(ValidationSimulationError):
        await run_validation_simulation(code, game_name, team_name)


def test_allowed_modules():
    assert "random" in ALLOWED_MODULES
    assert "games" in ALLOWED_MODULES
    assert "player" in ALLOWED_MODULES


def test_risky_functions():
    assert "eval" in RISKY_FUNCTIONS
    assert "exec" in RISKY_FUNCTIONS
    assert "open" in RISKY_FUNCTIONS


if __name__ == "__main__":
    pytest.main(["-v", "-s"])
