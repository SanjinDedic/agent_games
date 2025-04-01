# tests/integration/test_game_workflows.py

import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.database.db_models import League, SimulationResult, Submission, Team
from backend.routes.auth.auth_core import create_access_token

pytestmark = pytest.mark.usefixtures("ensure_containers")


@pytest.fixture
def setup_integration_team(db_session: Session, test_league: League) -> Team:
    """Create a test team with basic submission"""
    team = Team(
        name="integration_test_team",
        school_name="Integration Test School",
        password_hash="test_hash",
        league_id=test_league.id,
        institution_id=test_league.institution_id,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    # Add a basic valid submission
    submission = Submission(
        code="""
from games.prisoners_dilemma.player import Player
class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "collude"
""",
        timestamp=datetime.now(),
        team_id=team.id,
    )
    db_session.add(submission)
    db_session.commit()

    return team


def test_complete_game_lifecycle(
    client: TestClient,
    db_session: Session,
    auth_headers: dict,
    team_auth_headers: dict,
):
    """
    Test complete lifecycle from league creation through game completion.
    This test verifies the entire flow of:
    1. League creation
    2. Team creation and assignment
    3. Code submission
    4. Running simulations
    5. Publishing results
    6. Viewing results
    """

    # 1. Create a new league
    # The headers need to be institution headers
    inst_token = create_access_token(
        data={"sub": "integration_team", "role": "institution"},
        expires_delta=timedelta(minutes=30),
    )
    auth_headers = {"Authorization": f"Bearer {inst_token}"}

    league_response = client.post(
        "/institution/league-create",
        headers=auth_headers,
        json={"name": "integration_league", "game": "prisoners_dilemma"},
    )
    assert league_response.status_code == 200
    league_data = league_response.json()
    assert league_data["status"] == "success"
    league_id = league_data["data"]["league_id"]

    # 2. Create and assign team
    team_response = client.post(
        "/admin/team-create",
        headers=auth_headers,
        json={
            "name": "integration_team",
            "password": "test_pass",
            "school_name": "Integration School",
        },
    )
    assert team_response.status_code == 200
    assert team_response.json()["status"] == "success"

    # Create team token and headers
    team_token = create_access_token(
        data={"sub": "integration_team", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    team_headers = {"Authorization": f"Bearer {team_token}"}

    # Assign team to league
    assign_response = client.post(
        "/user/league-assign",
        headers=team_headers,
        json={"name": "integration_league"},
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["status"] == "success"

    # 3. Submit code
    code = """
from games.prisoners_dilemma.player import Player
class CustomPlayer(Player):
    def make_decision(self, game_state):
        self.add_feedback(f"Round {game_state['round_number']}")
        return "collude" if game_state['round_number'] % 2 == 0 else "defect"
"""
    submit_response = client.post(
        "/user/submit-agent",
        headers=team_headers,
        json={"code": code},
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "success"

    # 4. Run simulation
    sim_response = client.post(
        "/admin/run-simulation",
        headers=auth_headers,
        json={
            "league_id": league_id,
            "num_simulations": 10,
            "custom_rewards": [4, 0, 6, 2],
        },
    )
    assert sim_response.status_code == 200
    sim_data = sim_response.json()
    assert sim_data["status"] == "success"
    sim_id = sim_data["data"]["id"]

    # 5. Publish results
    publish_response = client.post(
        "/admin/publish-results",
        headers=auth_headers,
        json={
            "league_name": "integration_league",
            "id": sim_id,
            "feedback": "Integration test simulation results",
        },
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "success"

    # 6. View results (as team)
    results_response = client.post(
        "/user/get-published-results-for-league",
        json={"name": "integration_league"},
    )
    assert results_response.status_code == 200
    results_data = results_response.json()
    assert results_data["status"] == "success"
    assert results_data["data"] is not None
    assert "total_points" in results_data["data"]


@pytest.mark.asyncio
async def test_concurrent_game_operations(
    client: TestClient,
    db_session: Session,
    auth_headers: dict,
):
    """
    Test system behavior under concurrent operations.
    This tests:
    1. Multiple simultaneous submissions
    2. Concurrent simulation runs
    3. Concurrent result publishing
    """
    # Setup league
    league_response = client.post(
        "/admin/league-create",
        headers=auth_headers,
        json={"name": "concurrent_league", "game": "prisoners_dilemma"},
    )
    league_id = league_response.json()["data"]["league_id"]

    # Create multiple teams
    teams = []
    team_headers = []
    for i in range(3):
        team_response = client.post(
            "/admin/team-create",
            headers=auth_headers,
            json={
                "name": f"concurrent_team_{i}",
                "password": "test_pass",
                "school_name": f"Concurrent School {i}",
            },
        )
        teams.append(team_response.json()["data"])

        # Create team token and headers
        team_token = create_access_token(
            data={"sub": f"concurrent_team_{i}", "role": "student"},
            expires_delta=timedelta(minutes=30),
        )
        team_headers.append({"Authorization": f"Bearer {team_token}"})

        # Assign to league
        client.post(
            "/user/league-assign",
            headers={"Authorization": f"Bearer {team_token}"},
            json={"name": "concurrent_league"},
        )

    # 1. Test concurrent submissions
    async def submit_code(headers, variation):
        return client.post(
            "/user/submit-agent",
            headers=headers,
            json={
                "code": f"""
from games.prisoners_dilemma.player import Player
class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "{'collude' if variation % 2 == 0 else 'defect'}"
"""
            },
        )

    submission_tasks = [
        submit_code(headers, i) for i, headers in enumerate(team_headers)
    ]
    submission_responses = await asyncio.gather(*submission_tasks)
    for response in submission_responses:
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    # 2. Test concurrent simulation runs
    async def run_simulation():
        return client.post(
            "/admin/run-simulation",
            headers=auth_headers,
            json={
                "league_id": league_id,
                "num_simulations": 10,
            },
        )

    sim_tasks = [run_simulation() for _ in range(3)]
    sim_responses = await asyncio.gather(*sim_tasks)
    sim_ids = []
    for response in sim_responses:
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        sim_ids.append(data["data"]["id"])

    # 3. Test concurrent result publishing
    async def publish_results(sim_id):
        return client.post(
            "/admin/publish-results",
            headers=auth_headers,
            json={
                "league_name": "concurrent_league",
                "id": sim_id,
                "feedback": f"Concurrent simulation {sim_id} results",
            },
        )

    publish_tasks = [publish_results(sim_id) for sim_id in sim_ids]
    publish_responses = await asyncio.gather(*publish_tasks)
    for response in publish_responses:
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    # Verify final state
    results_response = client.post(
        "/user/get-published-results-for-league",
        json={"name": "concurrent_league"},
    )
    assert results_response.status_code == 200
    results_data = results_response.json()
    assert results_data["status"] == "success"
    assert results_data["data"] is not None
