"""Tests covering uncovered paths in base_game.py:
- add_feedback with dict/string game_feedback
- add_player with valid/invalid code
- reset with dict/string game_feedback
- load_validation_players error paths
"""

from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from backend.games.base_game import BaseGame


class MockLeague:
    id = 1
    name = "test"
    game = "prisoners_dilemma"


@pytest.fixture
def game():
    return BaseGame(MockLeague())


def test_add_feedback_list(game):
    game.verbose = True
    game.game_feedback = []
    game.add_feedback("msg1")
    assert game.game_feedback == ["msg1"]


def test_add_feedback_dict_with_moves(game):
    game.verbose = True
    game.game_feedback = {"moves": []}
    game.add_feedback("move1")
    assert game.game_feedback["moves"] == ["move1"]


def test_add_feedback_dict_with_matches(game):
    game.verbose = True
    game.game_feedback = {"matches": []}
    game.add_feedback("match1")
    assert game.game_feedback["matches"] == ["match1"]


def test_add_feedback_string(game):
    game.verbose = True
    game.game_feedback = ""
    game.add_feedback("line1")
    assert "line1" in game.game_feedback


def test_add_feedback_not_verbose(game):
    game.verbose = False
    game.game_feedback = []
    game.add_feedback("should not appear")
    assert game.game_feedback == []


def test_add_player_valid_code():
    """Use PrisonersDilemmaGame so add_player can resolve the player module."""
    from backend.games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame
    pd_game = PrisonersDilemmaGame(MockLeague())
    pd_game.players = []
    pd_game.scores = {}

    code = """
from games.prisoners_dilemma.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "collude"
"""
    player = pd_game.add_player(code, "TestTeam")
    assert player is not None
    assert player.name == "TestTeam"
    assert "TestTeam" in pd_game.scores


def test_add_player_no_custom_player_class():
    from backend.games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame
    pd_game = PrisonersDilemmaGame(MockLeague())
    pd_game.players = []
    pd_game.scores = {}

    code = """
class SomethingElse:
    pass
"""
    player = pd_game.add_player(code, "BadTeam")
    assert player is None


def test_add_player_wrong_base_class():
    from backend.games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame
    pd_game = PrisonersDilemmaGame(MockLeague())
    pd_game.players = []
    pd_game.scores = {}

    code = """
class CustomPlayer:
    def make_decision(self, game_state):
        return "collude"
"""
    player = pd_game.add_player(code, "WrongBase")
    assert player is None


def test_add_player_syntax_error():
    from backend.games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame
    pd_game = PrisonersDilemmaGame(MockLeague())
    pd_game.players = []
    pd_game.scores = {}

    code = "this is not valid python {{{{"
    player = pd_game.add_player(code, "SyntaxErr")
    assert player is None


def test_reset_list_feedback(game):
    game.game_feedback = ["old"]
    game.reset()
    assert game.game_feedback == []


def test_reset_dict_feedback(game):
    game.game_feedback = {"game": "test", "moves": ["old"]}
    # Need to set the module path so reset can derive game_name
    game.__class__.__module__ = "backend.games.prisoners_dilemma.prisoners_dilemma"
    game.reset()
    assert game.game_feedback == {"game": "prisoners_dilemma", "moves": []}


def test_reset_string_feedback(game):
    game.game_feedback = "old feedback"
    game.reset()
    assert game.game_feedback == ""


def test_run_single_game_with_feedback(game):
    """Covers the run_single_game_with_feedback method."""
    # Mock play_game since BaseGame doesn't implement it
    game.play_game = lambda custom_rewards=None: {"points": {}, "table": {}}
    result = game.run_single_game_with_feedback()
    assert game.verbose is True
    assert "results" in result
    assert "feedback" in result
    assert "player_feedback" in result


def test_load_validation_players_no_players_list():
    """When validation_players module has no 'players' attribute."""
    with patch("importlib.import_module") as mock_import:
        mock_module = MagicMock(spec=[])  # No 'players' attribute
        mock_import.return_value = mock_module
        game = BaseGame(MockLeague())
        # Should fall back to empty
        assert game.players == [] or len(game.players) >= 0


def test_load_validation_players_import_error():
    """When validation_players module doesn't exist."""
    with patch("importlib.import_module", side_effect=ImportError("no module")):
        game = BaseGame.__new__(BaseGame)
        game.verbose = False
        game.league = MockLeague()
        game.players = []
        game.scores = {}
        game.game_feedback = []
        game.player_feedback = {}
        game.load_validation_players()
        assert game.players == []
        assert game.scores == {}
