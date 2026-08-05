"""Integration tests for /user/submit-agent-result.

The endpoint persists agent validations the browser already ran — via Pyodide
(frontend/src/pyodide/validation_harness.py) or via the browser's direct call
to the validation Lambda (tagged, covered in test_submit_agent_fallback.py).
No server-side execution is involved anywhere in this file — that is the
point of the endpoint. Hint requests ride the same endpoint with
?generate_hint=true (covered in test_user_agent.py).
"""

from datetime import timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import (
    League,
    Submission,
    SubmissionMetadata,
    Team,
)
from backend.routes.user.user_models import MAX_RESULT_STDOUT_CHARS
from backend.tests.conftest import make_student_token
from backend.time_utils import utc_now

VALID_CODE = (
    "from games.greedy_pig.player import Player\n"
    "class CustomPlayer(Player):\n"
    "    def make_decision(self, game_state):\n"
    "        return 'bank'\n"
)

TEAM_NAME = "pyodide_result_team"


@pytest.fixture
def league_team(db_session: Session) -> Team:
    """A team in a greedy_pig league (the seed teams sit in 'unassigned',
    which the endpoint rejects)."""
    league = League(
        name="pyodide_result_league",
        game="greedy_pig",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
    )
    db_session.add(league)
    db_session.flush()
    team = Team(
        name=TEAM_NAME,
        school_name="Test School",
        password_hash="test_hash",
        league_id=league.id,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


@pytest.fixture
def result_headers(league_team: Team) -> dict:
    return {"Authorization": f"Bearer {make_student_token(league_team)}"}


def make_payload(**overrides):
    payload = {
        "code": VALID_CODE,
        "status": "success",
        "message": None,
        "feedback": {"game": "greedy_pig", "rounds": []},
        "simulation_results": {
            "total_points": {
                TEAM_NAME: 500,
                "Bot1": 700,
                "Bot2": 300,
                "Bot3": 100,
            },
            "num_simulations": 300,
            "table": {},
            "strategies": {"Bot1": "always banks early"},
        },
        "duration_ms": 812.5,
        "stdout": None,
    }
    payload.update(overrides)
    return payload


def test_successful_result_is_stored_with_server_computed_ranking(
    client, db_session, league_team, result_headers
):
    response = client.post(
        "/user/submit-agent-result", json=make_payload(), headers=result_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["team_name"] == TEAM_NAME
    assert data["results"]["num_simulations"] == 300
    assert data["feedback"]["game"] == "greedy_pig"
    assert data["duration_ms"] == 812.5
    assert data["hint"] is None
    assert data["hint_available"] is False
    assert data["hint_cancelled"] is False

    submission = db_session.exec(
        select(Submission).where(Submission.id == data["submission_id"])
    ).one()
    assert submission.code == VALID_CODE
    # Only Bot1 (700) outscores the team (500) -> rank 2
    assert submission.ranking == 2
    assert submission.meta.duration_ms == 812.5
    assert submission.meta.league_id == league_team.league_id

    # The normal latest-submission endpoint serves it back
    response = client.get("/user/get-team-submission", headers=result_headers)
    assert response.json()["code"] == VALID_CODE


def test_missing_team_in_results_stores_ranking_none(
    client, db_session, result_headers
):
    payload = make_payload(
        simulation_results={"total_points": {"Bot1": 10}, "num_simulations": 1}
    )
    response = client.post(
        "/user/submit-agent-result", json=payload, headers=result_headers
    )
    assert response.status_code == 200
    submission = db_session.exec(
        select(Submission).where(
            Submission.id == response.json()["submission_id"]
        )
    ).one()
    assert submission.ranking is None

    response = client.post(
        "/user/submit-agent-result",
        json=make_payload(simulation_results=None),
        headers=result_headers,
    )
    assert response.status_code == 200


def test_unsafe_code_is_rejected_regardless_of_claimed_status(
    client, db_session, league_team, result_headers
):
    """The server-side AST gate wins over the client-claimed success: stored
    submissions are later executed in teachers' browsers."""
    payload = make_payload(code="import os\nos.system('ls')\n")
    response = client.post(
        "/user/submit-agent-result", json=payload, headers=result_headers
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"].startswith("Agent code is not safe:")
    assert data["hint"] is None
    assert "hint_available" in data

    # Metadata-only: the attempt is recorded, the code is not
    assert db_session.exec(select(Submission)).all() == []
    (meta,) = db_session.exec(select(SubmissionMetadata)).all()
    assert meta.team_id == league_team.id


def test_client_reported_error_records_metadata_only(
    client, db_session, result_headers
):
    payload = make_payload(
        status="error",
        message="Error during simulation: division by zero",
        feedback=None,
        simulation_results=None,
        duration_ms=None,
    )
    response = client.post(
        "/user/submit-agent-result", json=payload, headers=result_headers
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Error during simulation: division by zero"
    assert "hint_available" in data

    assert db_session.exec(select(Submission)).all() == []
    assert len(db_session.exec(select(SubmissionMetadata)).all()) == 1


def test_rate_limit_is_shared_with_submit_agent(
    client, db_session, league_team, result_headers
):
    """Both endpoints count the same SubmissionMetadata budget, so a student
    can't double their 5/minute by mixing paths."""
    for _ in range(5):
        db_session.add(
            SubmissionMetadata(team_id=league_team.id, timestamp=utc_now())
        )
    db_session.commit()

    response = client.post(
        "/user/submit-agent-result", json=make_payload(), headers=result_headers
    )
    assert response.status_code == 429

    # Outside the window the budget resets
    for meta in db_session.exec(select(SubmissionMetadata)).all():
        meta.timestamp = utc_now() - timedelta(minutes=2)
        db_session.add(meta)
    db_session.commit()

    response = client.post(
        "/user/submit-agent-result", json=make_payload(), headers=result_headers
    )
    assert response.status_code == 200


def test_requires_team_token(client, admin_headers):
    response = client.post(
        "/user/submit-agent-result", json=make_payload(), headers=admin_headers
    )
    assert response.status_code in (400, 403)


def test_non_dict_simulation_results_rejected(client, result_headers):
    response = client.post(
        "/user/submit-agent-result",
        json=make_payload(simulation_results="not a dict"),
        headers=result_headers,
    )
    assert response.status_code == 422

    response = client.post(
        "/user/submit-agent-result",
        json=make_payload(status="weird"),
        headers=result_headers,
    )
    assert response.status_code == 422


def test_stdout_is_truncated_server_side(client, db_session, result_headers):
    response = client.post(
        "/user/submit-agent-result",
        json=make_payload(stdout="x" * (MAX_RESULT_STDOUT_CHARS * 2)),
        headers=result_headers,
    )
    assert response.status_code == 200


def test_traceback_is_accepted_and_bounded(client, result_headers):
    """The 7th envelope key feeds the hint context only; an oversized value
    is truncated by the same validator as stdout, never rejected."""
    response = client.post(
        "/user/submit-agent-result",
        json=make_payload(traceback="t" * (MAX_RESULT_STDOUT_CHARS * 2)),
        headers=result_headers,
    )
    assert response.status_code == 200
