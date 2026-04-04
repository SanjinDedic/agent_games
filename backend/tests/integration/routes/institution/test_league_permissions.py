"""Tests for institution-scoped league visibility and admin super-access.

Verifies that:
- Regular institutions see only their own leagues
- Admin role and Admin Institution (id=1) see all leagues
- Admin can simulate/publish/delete any institution's leagues
- Regular institutions cannot access other institutions' leagues
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from backend.database.db_models import (
    Institution,
    League,
    LeagueType,
    SimulationResult,
    SimulationResultItem,
    Submission,
    Team,
    TeamType,
)
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def two_institutions(db_session: Session) -> dict:
    """Create two separate institutions, each with a league and teams."""
    now = datetime.now()

    # Get the Admin Institution (id=1, created by conftest)
    admin_inst = db_session.exec(
        select(Institution).where(Institution.name == "Admin Institution")
    ).first()
    assert admin_inst is not None

    # Institution A
    inst_a = Institution(
        name="PermTest Institution A",
        contact_person="Person A",
        contact_email="a@example.com",
        created_date=now,
        subscription_active=True,
        subscription_expiry=now + timedelta(days=30),
        docker_access=True,
        password_hash="hash_a",
    )
    db_session.add(inst_a)
    db_session.commit()
    db_session.refresh(inst_a)

    # Institution B
    inst_b = Institution(
        name="PermTest Institution B",
        contact_person="Person B",
        contact_email="b@example.com",
        created_date=now,
        subscription_active=True,
        subscription_expiry=now + timedelta(days=30),
        docker_access=True,
        password_hash="hash_b",
    )
    db_session.add(inst_b)
    db_session.commit()
    db_session.refresh(inst_b)

    # Unassigned leagues
    for inst in [inst_a, inst_b]:
        db_session.add(League(
            name="unassigned",
            created_date=now,
            expiry_date=now + timedelta(days=365),
            game="greedy_pig",
            league_type=LeagueType.INSTITUTION,
            institution_id=inst.id,
        ))
    db_session.commit()

    # League for A
    league_a = League(
        name="perm_league_a",
        created_date=now,
        expiry_date=now + timedelta(days=7),
        game="prisoners_dilemma",
        institution_id=inst_a.id,
    )
    db_session.add(league_a)
    db_session.commit()
    db_session.refresh(league_a)

    # League for B
    league_b = League(
        name="perm_league_b",
        created_date=now,
        expiry_date=now + timedelta(days=7),
        game="greedy_pig",
        institution_id=inst_b.id,
    )
    db_session.add(league_b)
    db_session.commit()
    db_session.refresh(league_b)

    # Teams + submissions for league A
    for i in range(2):
        team = Team(
            name=f"perm_team_a_{i}",
            school_name=f"School A{i}",
            password_hash="hash",
            league_id=league_a.id,
            institution_id=inst_a.id,
            team_type=TeamType.STUDENT,
        )
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)
        db_session.add(Submission(
            code='from games.prisoners_dilemma.player import Player\nclass CustomPlayer(Player):\n    def make_decision(self, game_state):\n        return "collude"',
            timestamp=now,
            team_id=team.id,
        ))

    # Teams + submissions for league B
    for i in range(2):
        team = Team(
            name=f"perm_team_b_{i}",
            school_name=f"School B{i}",
            password_hash="hash",
            league_id=league_b.id,
            institution_id=inst_b.id,
            team_type=TeamType.STUDENT,
        )
        db_session.add(team)
        db_session.commit()
        db_session.refresh(team)
        db_session.add(Submission(
            code='from games.greedy_pig.player import Player\nclass CustomPlayer(Player):\n    def make_decision(self, game_state):\n        if game_state["unbanked_money"][self.name] > 15:\n            return "bank"\n        return "continue"',
            timestamp=now,
            team_id=team.id,
        ))

    db_session.commit()

    # Tokens
    token_a = create_access_token(
        data={"sub": inst_a.name, "role": "institution", "institution_id": inst_a.id},
        expires_delta=timedelta(minutes=30),
    )
    token_b = create_access_token(
        data={"sub": inst_b.name, "role": "institution", "institution_id": inst_b.id},
        expires_delta=timedelta(minutes=30),
    )
    admin_token = create_access_token(
        data={"sub": "admin", "role": "admin"},
        expires_delta=timedelta(minutes=30),
    )
    admin_inst_token = create_access_token(
        data={"sub": admin_inst.name, "role": "institution", "institution_id": admin_inst.id},
        expires_delta=timedelta(minutes=30),
    )
    student_a_token = create_access_token(
        data={"sub": "perm_team_a_0", "role": "student", "institution_id": inst_a.id},
        expires_delta=timedelta(minutes=30),
    )
    student_no_inst_token = create_access_token(
        data={"sub": "orphan_student", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "admin_inst": admin_inst,
        "league_a": league_a,
        "league_b": league_b,
        "headers_a": {"Authorization": f"Bearer {token_a}"},
        "headers_b": {"Authorization": f"Bearer {token_b}"},
        "headers_admin": {"Authorization": f"Bearer {admin_token}"},
        "headers_admin_inst": {"Authorization": f"Bearer {admin_inst_token}"},
        "headers_student_a": {"Authorization": f"Bearer {student_a_token}"},
        "headers_student_no_inst": {"Authorization": f"Bearer {student_no_inst_token}"},
    }


def test_get_all_leagues_scoped(client, two_institutions):
    """Institutions see only their own leagues; admin sees all."""
    data = two_institutions

    # Institution A sees its leagues but not B's
    resp = client.get("/user/get-all-leagues", headers=data["headers_a"])
    assert resp.status_code == 200
    names = [l["name"] for l in resp.json()["data"]["leagues"]]
    assert "perm_league_a" in names
    assert "perm_league_b" not in names

    # Institution B sees its leagues but not A's
    resp = client.get("/user/get-all-leagues", headers=data["headers_b"])
    names = [l["name"] for l in resp.json()["data"]["leagues"]]
    assert "perm_league_b" in names
    assert "perm_league_a" not in names

    # Admin role sees all
    resp = client.get("/user/get-all-leagues", headers=data["headers_admin"])
    names = [l["name"] for l in resp.json()["data"]["leagues"]]
    assert "perm_league_a" in names
    assert "perm_league_b" in names

    # Admin Institution (id=1) sees all
    resp = client.get("/user/get-all-leagues", headers=data["headers_admin_inst"])
    names = [l["name"] for l in resp.json()["data"]["leagues"]]
    assert "perm_league_a" in names
    assert "perm_league_b" in names

    # Student with institution_id sees only their institution's leagues
    resp = client.get("/user/get-all-leagues", headers=data["headers_student_a"])
    names = [l["name"] for l in resp.json()["data"]["leagues"]]
    assert "perm_league_a" in names
    assert "perm_league_b" not in names

    # Student without institution_id gets empty list
    resp = client.get("/user/get-all-leagues", headers=data["headers_student_no_inst"])
    leagues = resp.json()["data"]["leagues"]
    assert leagues == []


def _mock_simulation_response(team_names):
    """Helper to build a mock httpx response for simulation."""
    mock_resp = type("MockResponse", (), {
        "status_code": 200,
        "json": lambda self: {
            "status": "success",
            "simulation_results": {
                "total_points": {name: 100 for name in team_names},
                "num_simulations": 10,
                "table": {},
            },
            "feedback": "test",
            "player_feedback": None,
        },
    })()

    async def mock_post(*args, **kwargs):
        return mock_resp

    return mock_post


def test_run_simulation_cross_institution(client, two_institutions):
    """Institution A cannot simulate B's league; admin can simulate any."""
    data = two_institutions
    team_names_b = ["perm_team_b_0", "perm_team_b_1"]

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = _mock_simulation_response(team_names_b)

        # Institution A CANNOT simulate B's league
        resp = client.post(
            "/institution/run-simulation",
            headers=data["headers_a"],
            json={"league_id": data["league_b"].id, "num_simulations": 10},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "error"
        assert "permission" in resp.json()["message"].lower()

        # Admin CAN simulate B's league
        resp = client.post(
            "/institution/run-simulation",
            headers=data["headers_admin"],
            json={"league_id": data["league_b"].id, "num_simulations": 10},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

        # Admin Institution CAN simulate B's league
        resp = client.post(
            "/institution/run-simulation",
            headers=data["headers_admin_inst"],
            json={"league_id": data["league_b"].id, "num_simulations": 10},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"


def test_publish_results_cross_institution(client, two_institutions, db_session):
    """Institution A cannot publish B's results; admin can."""
    data = two_institutions

    # Create a simulation result for league B
    sim = SimulationResult(
        league_id=data["league_b"].id,
        timestamp=datetime.now(),
        num_simulations=10,
        custom_rewards="[10,8,6]",
    )
    db_session.add(sim)
    db_session.commit()
    db_session.refresh(sim)

    # Institution A CANNOT publish B's results
    resp = client.post(
        "/institution/publish-results",
        headers=data["headers_a"],
        json={"league_name": "perm_league_b", "id": sim.id},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"

    # Admin CAN publish B's results
    resp = client.post(
        "/institution/publish-results",
        headers=data["headers_admin"],
        json={"league_name": "perm_league_b", "id": sim.id},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["data"]["published"] is True


def test_delete_league_cross_institution(client, two_institutions, db_session):
    """Institution A cannot delete B's league; admin can."""
    data = two_institutions

    # Create expendable leagues for deletion tests
    now = datetime.now()
    delete_target = League(
        name="perm_delete_target",
        created_date=now,
        expiry_date=now + timedelta(days=7),
        game="greedy_pig",
        institution_id=data["inst_b"].id,
    )
    db_session.add(delete_target)
    db_session.commit()

    # Institution A CANNOT delete B's league
    resp = client.post(
        "/institution/delete-league",
        headers=data["headers_a"],
        json={"name": "perm_delete_target"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "error"

    # Admin CAN delete B's league
    resp = client.post(
        "/institution/delete-league",
        headers=data["headers_admin"],
        json={"name": "perm_delete_target"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # Verify it's actually deleted
    league = db_session.exec(
        select(League).where(League.name == "perm_delete_target")
    ).first()
    assert league is None
