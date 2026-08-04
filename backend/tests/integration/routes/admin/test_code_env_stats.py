"""Integration tests for the code-environment usage counters.

Every game/exercise submission endpoint bumps a (user, kind, environment)
row in CodeEnvUsage; /admin/code-env-stats aggregates users and calls for
the admin "Code Env" tab. The lambda-path tests run the real local-subprocess
executors (no Lambda env vars in tests), same as the other submission tests.
"""

from datetime import timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import (
    CodeEnvUsage,
    Exercise,
    League,
    LeagueTutorial,
    Team,
    Tutorial,
)
from backend.tests.conftest import make_student_token
from backend.time_utils import utc_now

TEAM_NAME = "code_env_team"

VALID_AGENT_CODE = (
    "from games.greedy_pig.player import Player\n"
    "class CustomPlayer(Player):\n"
    "    def make_decision(self, game_state):\n"
    "        return 'bank'\n"
)

PASSING_EXERCISE_CODE = "def add(a, b):\n    return a + b\n"


@pytest.fixture
def league_team(db_session: Session) -> Team:
    """A team in a greedy_pig league (the seed teams sit in 'unassigned',
    which the agent endpoints reject)."""
    league = League(
        name="code_env_league",
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
def league_team_headers(league_team: Team) -> dict:
    return {"Authorization": f"Bearer {make_student_token(league_team)}"}


@pytest.fixture
def league_exercise(db_session: Session, league_team: Team) -> Exercise:
    """One exercise in a tutorial attached to the code-env team's league."""
    tutorial = Tutorial(
        title="Code Env Tutorial",
        description="Tutorial used by the code-env counter tests",
    )
    db_session.add(tutorial)
    db_session.flush()
    db_session.add(
        LeagueTutorial(league_id=league_team.league_id, tutorial_id=tutorial.id)
    )
    exercise = Exercise(
        tutorial_id=tutorial.id,
        order_index=0,
        title="Add",
        problem_markdown="Add two numbers",
        starter_code="def add(a, b):\n    pass\n",
        entry_function="add",
        test_code="def test_add():\n    check(add(1, 2), 3)\n",
    )
    db_session.add(exercise)
    db_session.commit()
    db_session.refresh(exercise)
    return exercise


def agent_result_payload(**overrides):
    payload = {
        "code": VALID_AGENT_CODE,
        "status": "success",
        "message": None,
        "feedback": None,
        "simulation_results": {
            "total_points": {TEAM_NAME: 500, "Bot1": 700},
            "num_simulations": 300,
            "table": {},
        },
        "duration_ms": 10.0,
        "stdout": None,
    }
    payload.update(overrides)
    return payload


def exercise_result_payload(exercise_id, **overrides):
    payload = {
        "exercise_id": exercise_id,
        "code": PASSING_EXERCISE_CODE,
        "status": "success",
        "passed": True,
        "test_results": [
            {
                "name": "adds",
                "call": None,
                "expected": 3,
                "actual": "3",
                "passed": True,
                "error": None,
            }
        ],
        "stdout": None,
        "duration_ms": 1.5,
    }
    payload.update(overrides)
    return payload


def usage_row(db_session, kind, environment):
    return db_session.exec(
        select(CodeEnvUsage).where(
            CodeEnvUsage.user_identifier == TEAM_NAME,
            CodeEnvUsage.kind == kind,
            CodeEnvUsage.environment == environment,
        )
    ).first()


def get_stats(client, admin_headers):
    response = client.get("/admin/code-env-stats", headers=admin_headers)
    assert response.status_code == 200
    return response.json()


def cell(stats, kind, environment):
    for row in stats["stats"]:
        if row["kind"] == kind and row["environment"] == environment:
            return row
    return None


def test_pyodide_game_submission_is_counted(
    client, db_session, league_team_headers, admin_headers
):
    for _ in range(2):
        response = client.post(
            "/user/submit-agent-result",
            json=agent_result_payload(),
            headers=league_team_headers,
        )
        assert response.status_code == 200

    row = usage_row(db_session, "game", "pyodide")
    assert row.call_count == 2

    stats = get_stats(client, admin_headers)
    assert cell(stats, "game", "pyodide") == {
        "kind": "game",
        "environment": "pyodide",
        "users": 1,
        "calls": 2,
    }


def test_lambda_game_submission_is_counted(
    client, db_session, league_team_headers
):
    response = client.post(
        "/user/submit-agent",
        json={"code": VALID_AGENT_CODE},
        headers=league_team_headers,
    )
    assert response.status_code == 200

    row = usage_row(db_session, "game", "lambda")
    assert row.call_count == 1
    assert usage_row(db_session, "game", "pyodide") is None


def test_failed_pyodide_game_submission_still_counted(
    client, db_session, league_team_headers
):
    """The counters track traffic, not success: a rejected submission ran
    code in the browser all the same."""
    response = client.post(
        "/user/submit-agent-result",
        json=agent_result_payload(code="import os"),
        headers=league_team_headers,
    )
    assert response.status_code == 400

    assert usage_row(db_session, "game", "pyodide").call_count == 1


def test_pyodide_exercise_submission_is_counted(
    client, db_session, league_team_headers, league_exercise
):
    response = client.post(
        "/tutorial/submit-exercise-result",
        json=exercise_result_payload(league_exercise.id),
        headers=league_team_headers,
    )
    assert response.status_code == 200

    assert usage_row(db_session, "exercise", "pyodide").call_count == 1


def test_lambda_exercise_submission_is_counted(
    client, db_session, league_team_headers, league_exercise
):
    response = client.post(
        "/tutorial/submit-exercise",
        json={"exercise_id": league_exercise.id, "code": PASSING_EXERCISE_CODE},
        headers=league_team_headers,
    )
    assert response.status_code == 200

    assert usage_row(db_session, "exercise", "lambda").call_count == 1


def test_totals_count_each_user_once_per_environment(
    client, db_session, league_team_headers, league_exercise, admin_headers
):
    """One user making game AND exercise Pyodide submissions is one user in
    the pyodide total, while the calls still add up."""
    response = client.post(
        "/user/submit-agent-result",
        json=agent_result_payload(),
        headers=league_team_headers,
    )
    assert response.status_code == 200
    response = client.post(
        "/tutorial/submit-exercise-result",
        json=exercise_result_payload(league_exercise.id),
        headers=league_team_headers,
    )
    assert response.status_code == 200

    stats = get_stats(client, admin_headers)
    assert stats["totals"]["pyodide"] == {"users": 1, "calls": 2}
    assert "lambda" not in stats["totals"]


def test_stats_requires_admin(client, student_headers):
    response = client.get("/admin/code-env-stats", headers=student_headers)
    assert response.status_code == 403


def test_stats_requires_auth(client):
    response = client.get("/admin/code-env-stats")
    assert response.status_code == 401


def test_stats_empty_when_no_traffic(client, admin_headers):
    stats = get_stats(client, admin_headers)
    assert stats == {"stats": [], "totals": {}}
