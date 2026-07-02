from datetime import datetime, timedelta

import pytest

from backend.database.db_models import League
from backend.games.base_game import BaseGame


@pytest.fixture
def test_league(db_session):
    """Create a test league for testing"""
    league = League(
        name="test_league",
        game="prisoners_dilemma",  # Use real game type
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=1),
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    return league


def test_base_game_initialization(test_league):
    """Test basic initialization of BaseGame"""
    game = BaseGame(test_league)
    assert game.verbose is False
    assert game.league == test_league
    assert isinstance(game.players, list)
    assert isinstance(game.scores, dict)
