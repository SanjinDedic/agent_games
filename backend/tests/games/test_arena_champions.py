import pytest
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from backend.database.db_models import Institution
from backend.routes.auth.auth_core import create_access_token


pytestmark = pytest.mark.usefixtures("ensure_containers")


def _create_institution(db_session: Session) -> Institution:
    inst = Institution(
        name="arena_inst",
        contact_person="Arena Admin",
        contact_email="arena@example.com",
        created_date=datetime.now(),
        subscription_active=True,
        subscription_expiry=datetime.now() + timedelta(days=30),
        docker_access=True,
        password_hash="test_hash",
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)
    return inst


def _create_league(client: TestClient, institution_id: int) -> tuple[int, dict]:
    token = create_access_token(
        data={"sub": "arena_inst", "role": "institution", "institution_id": institution_id},
        expires_delta=timedelta(minutes=30),
    )
    headers = {"Authorization": f"Bearer {token}"}

    league_name = "arena_league"
    resp = client.post(
        "/institution/league-create",
        headers=headers,
        json={"name": league_name, "game": "arena_champions"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return data["league_id"], headers


def _create_team_and_assign(client: TestClient, headers: dict, league_id: int, team_name: str = "arena_team") -> tuple[int, str]:
    # Create team (initially goes to unassigned league for the institution)
    create_resp = client.post(
        "/institution/team-create",
        headers=headers,
        json={
            "name": team_name,
            "password": "pw",
            "school_name": "Arena School",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    team_id = create_resp.json()["data"]["team_id"]

    # Assign to our arena league
    assign_resp = client.post(
        "/institution/assign-team-to-league",
        headers=headers,
        json={"team_id": team_id, "league_id": league_id},
    )
    assert assign_resp.status_code == 200, assign_resp.text

    return team_id, team_name


def _team_headers(team_name: str, team_id: int, league_id: int) -> dict:
    token = create_access_token(
        data={
            "sub": team_name,
            "role": "student",
            "team_id": team_id,
            "league_id": league_id,
        },
        expires_delta=timedelta(minutes=30),
    )
    return {"Authorization": f"Bearer {token}"}


def test_submit_agent_success(client: TestClient, db_session: Session):
    inst = _create_institution(db_session)
    league_id, inst_headers = _create_league(client, inst.id)
    team_id, team_name = _create_team_and_assign(client, inst_headers, league_id)
    headers = _team_headers(team_name, team_id, league_id)

    valid_agent_code = """
from games.arena_champions.player import Player
class CustomPlayer(Player):
    def __init__(self):
        super().__init__()
        # proportions within [0.2, 0.4] and sum to 1.0
        self.attack_proportion = 0.30
        self.defense_proportion = 0.20
        self.max_health_proportion = 0.25
        self.dexterity_proportion = 0.25
        self.set_to_original_stats()

    def make_combat_decision(self, opponent_stats, turn, your_role, last_opponent_action=None):
        return "attack" if your_role == "attacker" else "defend"
"""

    resp = client.post(
        "/user/submit-agent",
        headers=headers,
        json={"code": valid_agent_code},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "success", body


def test_submission_fails_when_sum_proportions_exceeds_one(client: TestClient, db_session: Session):
    inst = _create_institution(db_session)
    league_id, inst_headers = _create_league(client, inst.id)
    team_id, team_name = _create_team_and_assign(client, inst_headers, league_id, team_name="arena_team_sum_fail")
    headers = _team_headers(team_name, team_id, league_id)

    # Each within [0.2, 0.4], but sum = 1.2 (should fail validation in play_game)
    bad_sum_code = """
from games.arena_champions.player import Player
class CustomPlayer(Player):
    def __init__(self):
        super().__init__()
        self.attack_proportion = 0.40
        self.defense_proportion = 0.40
        self.max_health_proportion = 0.20
        self.dexterity_proportion = 0.20
        self.set_to_original_stats()

    def make_combat_decision(self, opponent_stats, turn, your_role, last_opponent_action=None):
        return "attack" if your_role == "attacker" else "defend"
"""

    resp = client.post(
        "/user/submit-agent",
        headers=headers,
        json={"code": bad_sum_code},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "error", body


def test_submission_fails_when_max_health_out_of_range(client: TestClient, db_session: Session):
    inst = _create_institution(db_session)
    league_id, inst_headers = _create_league(client, inst.id)
    team_id, team_name = _create_team_and_assign(client, inst_headers, league_id, team_name="arena_team_max_fail")
    headers = _team_headers(team_name, team_id, league_id)

    # Intentional bad out-of-range proportion (mirrors the idea of an excessively large value)
    bad_max_code = """
from games.arena_champions.player import Player
class CustomPlayer(Player):
    def __init__(self):
        super().__init__()
        self.attack_proportion = 0.30
        self.defense_proportion = 0.20
        self.max_health_proportion = 11111  # invalid
        self.dexterity_proportion = 0.25
        self.set_to_original_stats()

    def make_combat_decision(self, opponent_stats, turn, your_role, last_opponent_action=None):
        return "attack" if your_role == "attacker" else "defend"
"""

    resp = client.post(
        "/user/submit-agent",
        headers=headers,
        json={"code": bad_max_code},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "error", body
