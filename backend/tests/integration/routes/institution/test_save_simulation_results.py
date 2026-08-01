"""Tests for POST /institution/save-simulation-results.

The endpoint persists results computed by the in-browser (Pyodide) simulation
runner: no Celery round-trip, the server only checks ownership/shape and
stores via save_simulation_results.
"""

import json
from datetime import timedelta

import pytest
from sqlmodel import Session, select

from backend.tests.conftest import build_institution
from backend.database.db_models import (League, SimulationResult,
                                        SimulationResultItem, Team)
from backend.routes.auth.auth_core import create_access_token
from backend.time_utils import utc_now


TEAM_NAMES = ["sim_save_team_0", "sim_save_team_1", "sim_save_team_2"]


def _make_league_with_teams(db_session: Session, institution_id: int) -> League:
    league = League(
        name="save_sim_test_league",
        game="greedy_pig",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        institution_id=institution_id,
    )
    db_session.add(league)
    db_session.commit()

    for name in TEAM_NAMES:
        db_session.add(
            Team(
                name=name,
                school_name="Test School",
                password_hash="hash",
                league_id=league.id,
                institution_id=institution_id,
            )
        )
    db_session.commit()
    return league


@pytest.fixture
def save_setup(db_session: Session) -> tuple:
    institution = build_institution(
        name="test_institution",
        contact_person="Test Person",
        contact_email="test@example.com",
        created_date=utc_now(),
        subscription_active=True,
        subscription_expiry=utc_now() + timedelta(days=30),
        password_hash="test_hash",
    )
    db_session.add(institution)
    db_session.commit()
    db_session.refresh(institution)

    league = _make_league_with_teams(db_session, institution.id)

    token = create_access_token(
        data={
            "sub": institution.name,
            "role": "institution",
            "institution_id": institution.id,
        },
        expires_delta=timedelta(minutes=30),
    )
    headers = {"Authorization": f"Bearer {token}"}
    return institution, league, headers


def _payload(league_id: int, **overrides) -> dict:
    payload = {
        "league_id": league_id,
        "num_simulations": 100,
        "requested_simulations": 100,
        "capped": False,
        "custom_rewards": [10, 0, 0, 0, 0, 0, 0],
        "total_points": {TEAM_NAMES[0]: 640.0, TEAM_NAMES[1]: 360.0},
        "table": {},
        "strategies": {},
        "feedback": {"game": "greedy_pig", "rounds": [], "final_results": {}},
    }
    payload.update(overrides)
    return payload


def test_save_results_success_and_downstream_publish(
    client, save_setup, db_session
):
    """Happy path stores rows and the stored id publishes + reads back."""
    institution, league, headers = save_setup

    response = client.post(
        "/institution/save-simulation-results",
        headers=headers,
        json=_payload(league.id),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["league_name"] == league.name
    assert data["total_points"] == {TEAM_NAMES[0]: 640.0, TEAM_NAMES[1]: 360.0}
    assert data["num_simulations"] == 100
    assert data["requested_simulations"] == 100
    assert data["capped"] is False
    assert data["rewards"] == [10, 0, 0, 0, 0, 0, 0]
    assert data["feedback"]["game"] == "greedy_pig"
    assert data["timestamp"] is not None

    sim_result = db_session.exec(
        select(SimulationResult).where(SimulationResult.id == data["id"])
    ).one()
    assert sim_result.num_simulations == 100
    assert sim_result.custom_rewards == json.dumps([10, 0, 0, 0, 0, 0, 0])
    assert sim_result.feedback_str is None
    assert json.loads(sim_result.feedback_json)["game"] == "greedy_pig"

    items = db_session.exec(
        select(SimulationResultItem).where(
            SimulationResultItem.simulation_result_id == sim_result.id
        )
    ).all()
    scores_by_team = {item.team_id: item.score for item in items}
    teams = {
        t.name: t.id
        for t in db_session.exec(
            select(Team).where(Team.league_id == league.id)
        ).all()
    }
    assert scores_by_team == {
        teams[TEAM_NAMES[0]]: 640.0,
        teams[TEAM_NAMES[1]]: 360.0,
    }

    # The stored run publishes and reads back through the public link.
    response = client.post(
        "/institution/publish-results",
        headers=headers,
        json={"league_id": league.id, "id": sim_result.id, "feedback": None},
    )
    assert response.status_code == 200
    db_session.refresh(sim_result)
    assert sim_result.published is True
    assert sim_result.publish_link

    response = client.get(f"/user/published-result/{sim_result.publish_link}")
    assert response.status_code == 200
    published = response.json()
    assert published["total_points"] == {
        TEAM_NAMES[0]: 640.0,
        TEAM_NAMES[1]: 360.0,
    }


def test_save_results_string_feedback_stored_as_str(
    client, save_setup, db_session
):
    _, league, headers = save_setup

    response = client.post(
        "/institution/save-simulation-results",
        headers=headers,
        json=_payload(league.id, feedback="## Markdown feedback"),
    )
    assert response.status_code == 200

    sim_result = db_session.exec(
        select(SimulationResult).where(
            SimulationResult.id == response.json()["id"]
        )
    ).one()
    assert sim_result.feedback_str == "## Markdown feedback"
    assert sim_result.feedback_json is None


def test_save_results_table_stored_as_custom_values(
    client, save_setup, db_session
):
    """Table columns land in the custom_valueN slots (first three columns)."""
    _, league, headers = save_setup

    table = {
        "wins": {TEAM_NAMES[0]: 60, TEAM_NAMES[1]: 40},
        "rolls": {TEAM_NAMES[0]: 512, TEAM_NAMES[1]: 498},
    }
    response = client.post(
        "/institution/save-simulation-results",
        headers=headers,
        json=_payload(league.id, table=table),
    )
    assert response.status_code == 200
    assert response.json()["table"] == table

    items = db_session.exec(
        select(SimulationResultItem).where(
            SimulationResultItem.simulation_result_id == response.json()["id"]
        )
    ).all()
    assert {item.custom_value1_name for item in items} == {"wins"}
    assert {item.custom_value2_name for item in items} == {"rolls"}


def test_save_results_unknown_team_rejected(client, save_setup, db_session):
    """Names not in the league 400 instead of being silently dropped."""
    _, league, headers = save_setup

    before = len(db_session.exec(select(SimulationResult)).all())
    response = client.post(
        "/institution/save-simulation-results",
        headers=headers,
        json=_payload(
            league.id,
            total_points={TEAM_NAMES[0]: 640.0, "Bank5": 360.0},
        ),
    )
    assert response.status_code == 400
    assert "Bank5" in response.json()["detail"]
    after = len(db_session.exec(select(SimulationResult)).all())
    assert after == before


def test_save_results_rejects_unassigned_league(client, save_setup, db_session):
    institution, _, headers = save_setup

    unassigned = League(
        name="unassigned",
        game="greedy_pig",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        institution_id=institution.id,
    )
    db_session.add(unassigned)
    db_session.commit()

    response = client.post(
        "/institution/save-simulation-results",
        headers=headers,
        json=_payload(unassigned.id, total_points={}),
    )
    assert response.status_code == 400
    assert "unassigned" in response.json()["detail"].lower()


def test_save_results_foreign_league_404_and_admin_bypass(
    client, save_setup, db_session
):
    """Another institution's league 404s; an admin token bypasses ownership."""
    _, league, _ = save_setup

    other = build_institution(
        name="other_institution",
        contact_person="Other Person",
        contact_email="other@example.com",
        created_date=utc_now(),
        subscription_active=True,
        subscription_expiry=utc_now() + timedelta(days=30),
        password_hash="other_hash",
    )
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    other_token = create_access_token(
        data={
            "sub": other.name,
            "role": "institution",
            "institution_id": other.id,
        },
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/institution/save-simulation-results",
        headers={"Authorization": f"Bearer {other_token}"},
        json=_payload(league.id),
    )
    assert response.status_code == 404

    admin_token = create_access_token(
        data={"sub": "admin", "role": "admin", "institution_id": 1},
        expires_delta=timedelta(minutes=30),
    )
    response = client.post(
        "/institution/save-simulation-results",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=_payload(league.id),
    )
    assert response.status_code == 200


def test_save_results_validation_errors(client, save_setup):
    _, league, headers = save_setup

    # Completed more games than requested
    response = client.post(
        "/institution/save-simulation-results",
        headers=headers,
        json=_payload(league.id, num_simulations=200, requested_simulations=100),
    )
    assert response.status_code == 422

    # Bounds
    for bad in [
        {"num_simulations": 0},
        {"num_simulations": 10001, "requested_simulations": 10001},
        {"requested_simulations": 10001},
    ]:
        response = client.post(
            "/institution/save-simulation-results",
            headers=headers,
            json=_payload(league.id, **bad),
        )
        assert response.status_code == 422, bad

    # No token
    response = client.post(
        "/institution/save-simulation-results", json=_payload(league.id)
    )
    assert response.status_code == 401
