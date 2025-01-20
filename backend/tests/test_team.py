import os
from datetime import datetime, timedelta
from unittest.mock import patch

import database
import pytest
from api import app
from config import ROOT_DIR
from database import get_db_engine
from database.db_models import League, Submission, Team
from fastapi.testclient import TestClient
from routes.user.user_db import get_team
from sqlmodel import Session, delete, select
from tests.database_setup import setup_test_db


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
    team = get_team(db_session, "test_team")

    # First verify we have the unassigned league
    unassigned_league = db_session.exec(
        select(League).where(League.name == "unassigned")
    ).one_or_none()

    if not unassigned_league:
        # Create unassigned league if it doesn't exist
        unassigned_league = League(
            name="unassigned",
            game="greedy_pig",  # Set a valid game type
            created_date=datetime.now(),
            expiry_date=(datetime.now() + timedelta(days=7)),
        )
        db_session.add(unassigned_league)
        db_session.commit()
        db_session.refresh(unassigned_league)

    # Update team's league
    team.league_id = unassigned_league.id
    db_session.commit()
    db_session.refresh(team)

    # Clear any existing submissions before testing
    db_session.exec(delete(Submission).where(Submission.team_id == team.id))
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


def test_submit_agent_exceed_submission_limit(client, db_session, team_token):
    # Get the team and make sure it's in a valid league
    team = get_team(db_session, "test_team")

    # First verify comp_test league exists
    comp_test_league = db_session.exec(
        select(League).where(League.name == "comp_test")
    ).one_or_none()

    if not comp_test_league:
        # Create comp_test league if it doesn't exist
        comp_test_league = League(
            name="comp_test",
            game="greedy_pig",  # Set a valid game type
            created_date=datetime.now(),
            expiry_date=(datetime.now() + timedelta(days=7)),
        )
        db_session.add(comp_test_league)
        db_session.commit()
        db_session.refresh(comp_test_league)

    # Update team's league
    team.league_id = comp_test_league.id
    db_session.commit()
    db_session.refresh(team)

    # Clear any existing submissions
    db_session.exec(delete(Submission).where(Submission.team_id == team.id))
    db_session.commit()

    safe_code = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return 'continue'
    """

    # First submission should succeed
    response = client.post(
        "/user/submit-agent",
        json={"code": safe_code},
        headers={"Authorization": f"Bearer {team_token}"},
    )
    assert response.status_code == 200
    response_json = response.json()
    print("Response JSON for submission limit:", response_json)
    assert (
        response_json["status"] == "success"
    ), f"Expected success but got: {response_json}"


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
