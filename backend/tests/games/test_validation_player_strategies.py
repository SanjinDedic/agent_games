"""Every validation player must describe its strategy.

The `strategy` class attribute is shipped with simulation results and shown
as a tooltip on the player's name in the frontend rankings tables, so a
missing or empty one silently degrades the UI for that bot.
"""

import importlib

import pytest

from backend.config import GAMES


@pytest.mark.parametrize("game_name", GAMES)
def test_validation_players_declare_strategy(game_name):
    module = importlib.import_module(
        f"backend.games.{game_name}.validation_players"
    )
    assert module.players, f"{game_name} has no validation players"
    for player in module.players:
        strategy = getattr(player, "strategy", None)
        assert isinstance(strategy, str) and strategy.strip(), (
            f"{game_name}.{type(player).__name__} must declare a non-empty "
            "strategy class attribute"
        )
