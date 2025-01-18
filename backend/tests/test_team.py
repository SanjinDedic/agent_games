import os
from datetime import datetime, timedelta

import pytest
from sqlmodel import select

from backend.config import ROOT_DIR
from backend.database.db_models import League
from backend.routes.user.user_db import get_team


@pytest.fixture
def setup_test_leagues(db_session):
    comp_test = db_session.exec(
        select(League).where(League.name == "comp_test")
    ).first()
    if not comp_test:
        comp_test = League(
            name="comp_test",
            created_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=7),
            folder="leagues/admin/comp_test",
            game="greedy_pig",
        )
        db_session.add(comp_test)
        db_session.commit()
    return comp_test


def test_league_assign(client, team_token, setup_test_leagues):
    response = client.post(
        "/user/league-assign",
        json={"name": "comp_test"},
        headers={"Authorization": f"Bearer {team_token}"},
    )
    assert response.status_code == 200
    assert "success" in response.json()["status"]
    assert "assigned to league" in response.json()["message"]


def test_submit_agent_errors(client, db_session, team_token):
    # Test submitting unsafe code
    unsafe_code = """
import os

class CustomPlayer(Player):
    def make_decision(self, game_state):
        os.system('rm -rf /')
        return 'continue'
    """
    response = client.post(
        "/user/submit-agent",
        json={"code": unsafe_code},
        headers={"Authorization": f"Bearer {team_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "Agent code is not safe" in response.json()["message"]

    # Test submitting when team is assigned to the 'unassigned' league
    team = get_team(db_session, "test_team")  # Changed from BrunswickSC1
    unassigned_league = db_session.exec(
        select(League).where(League.name == "unassigned")
    ).one()
    team.league_id = unassigned_league.id
    db_session.commit()

    safe_code = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return 'continue'
    """
    response = client.post(
        "/user/submit-agent",
        json={"code": safe_code},
        headers={"Authorization": f"Bearer {team_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "Team is not assigned to a valid league" in response.json()["message"]


def test_submit_agent_with_unsafe_code(client, db_session, team_token):
    unsafe_code = """
import os

class CustomPlayer(Player):
    def make_decision(self, game_state):
        os.system('rm -rf /')
        return 'continue'
    """
    response = client.post(
        "/user/submit-agent",
        json={"code": unsafe_code},
        headers={"Authorization": f"Bearer {team_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "Agent code is not safe" in response.json()["message"]


def test_submit_agent_exceed_submission_limit(client, db_session, team_token):
    safe_code = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return 'continue'
    """
    for _ in range(6):
        response = client.post(
            "/user/submit-agent",
            json={"code": safe_code},
            headers={"Authorization": f"Bearer {team_token}"},
        )
        assert response.status_code == 200
        print("Response JSON for submission limit:", response.json())
        assert response.json()["status"] == "success"

    # 5th submission within a minute (should be rejected)
    response = client.post(
        "/user/submit-agent",
        json={"code": safe_code},
        headers={"Authorization": f"Bearer {team_token}"},
    )

    print("Response JSON for submission limit:", response.json())
    assert response.status_code == 200
    assert "You can only make 5 submissions per minute" in response.json()["message"]


def test_league_assign_error(client, team_token, db_session):
    # First, delete the league if it exists to ensure an error
    league = db_session.exec(select(League).where(League.name == "test_league")).first()
    if league:
        db_session.delete(league)
        db_session.commit()

    # Now try to assign team to non-existent league
    response = client.post(
        "/user/league-assign",
        json={"name": "test_league"},
        headers={"Authorization": f"Bearer {team_token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "League 'test_league' not found" in response.json()["message"]


def test_submit_agent_with_invalid_game(client, db_session, team_token):
    """Tests submitting code when team's league has an invalid game type.
    This will cover lines 198-200 in api.py where game type validation occurs."""

    # First modify the team's league to have an invalid game
    team = get_team(db_session, "test_team")
    team.league.game = "invalid_game"
    db_session.commit()

    # Note: Remove the leading whitespace in the code string
    code = """from games.greedy_pig.player import Player
class CustomPlayer(Player):
    def make_decision(self, game_state):
        return 'continue'"""

    response = client.post(
        "/user/submit-agent",
        json={"code": code},
        headers={"Authorization": f"Bearer {team_token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "Unknown game" in response.json()["message"]
    # Remove the invalid_game folder from the system
    league_path = os.path.join(ROOT_DIR, "games", "invalid_game")
    command = f"rm -rf {league_path}"
    os.system(command)
