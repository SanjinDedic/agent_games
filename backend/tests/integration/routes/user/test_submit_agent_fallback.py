"""Integration tests for the agent-validation Lambda-direct fallback telemetry.

When the browser can't run the validation Pyodide runner it calls the
validation Lambda's Function URL directly and persists that envelope through
/user/submit-agent-result tagged execution_source="pyodide_fallback"; every
such submission must be counted in the shared Valkey telemetry with the
"validation:" reason prefix, while the default (untagged Pyodide) path stays
byte-identical to before the feature existed. No execution happens anywhere
in this file — the endpoint only persists client-run envelopes.
"""

from datetime import timedelta

import pytest
import redis
from sqlmodel import Session, select

import backend.routes.tutorial.pyodide_support as pyodide_support
from backend.database.db_models import League, Submission, Team
from backend.tests.conftest import make_student_token
from backend.time_utils import utc_now

VALID_CODE = (
    "from games.greedy_pig.player import Player\n"
    "class CustomPlayer(Player):\n"
    "    def make_decision(self, game_state):\n"
    "        return 'bank'\n"
)


def make_payload(**overrides):
    """A successful validation envelope as the browser would submit it."""
    payload = {
        "code": VALID_CODE,
        "status": "success",
        "message": None,
        "feedback": {"game": "greedy_pig", "rounds": []},
        "simulation_results": {
            "total_points": {"pyodide_fallback_team": 500, "Bot1": 700},
            "num_simulations": 300,
        },
        "duration_ms": 812.5,
        "stdout": None,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def fallback_headers(db_session: Session) -> dict:
    """Headers for a team in a greedy_pig league (the seed teams sit in
    'unassigned', which submit-agent-result rejects)."""
    league = League(
        name="pyodide_fallback_league",
        game="greedy_pig",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
    )
    db_session.add(league)
    db_session.flush()
    team = Team(
        name="pyodide_fallback_team",
        school_name="Test School",
        password_hash="test_hash",
        league_id=league.id,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return {"Authorization": f"Bearer {make_student_token(team)}"}


def _today() -> str:
    return utc_now().strftime("%Y-%m-%d")


def test_fallback_submission_is_counted_with_validation_prefix(
    client, db_session, fallback_headers, valkey
):
    response = client.post(
        "/user/submit-agent-result",
        json=make_payload(
            execution_source="pyodide_fallback",
            fallback_reason="probe-timeout",
        ),
        headers=fallback_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["results"] is not None

    submission = db_session.exec(
        select(Submission).where(Submission.id == data["submission_id"])
    ).one()
    assert submission.code == VALID_CODE

    assert valkey.get(f"pyodide-fallback:count:{_today()}") == "1"
    assert valkey.hgetall(f"pyodide-fallback:reasons:{_today()}") == {
        "validation:probe-timeout": "1"
    }
    assert valkey.ttl(f"pyodide-fallback:count:{_today()}") > 0


def test_default_submission_is_not_counted(
    client, fallback_headers, valkey
):
    """The default Pyodide path must stay byte-identical: no counting."""
    response = client.post(
        "/user/submit-agent-result",
        json=make_payload(),
        headers=fallback_headers,
    )
    assert response.status_code == 200
    assert valkey.get(f"pyodide-fallback:count:{_today()}") is None


def test_missing_reason_counts_as_unspecified(
    client, fallback_headers, valkey
):
    response = client.post(
        "/user/submit-agent-result",
        json=make_payload(execution_source="pyodide_fallback"),
        headers=fallback_headers,
    )
    assert response.status_code == 200
    assert valkey.hgetall(f"pyodide-fallback:reasons:{_today()}") == {
        "validation:unspecified": "1"
    }


def test_oversized_reason_is_truncated(
    client, fallback_headers, valkey
):
    response = client.post(
        "/user/submit-agent-result",
        json=make_payload(
            execution_source="pyodide_fallback",
            fallback_reason="x" * 2000,
        ),
        headers=fallback_headers,
    )
    assert response.status_code == 200
    (reason,) = valkey.hgetall(f"pyodide-fallback:reasons:{_today()}")
    assert reason == "validation:" + "x" * 500


def test_unknown_execution_source_rejected(client, fallback_headers):
    response = client.post(
        "/user/submit-agent-result",
        json=make_payload(execution_source="celery"),
        headers=fallback_headers,
    )
    assert response.status_code == 422


def test_fallback_telemetry_failure_fails_open(
    client, fallback_headers, monkeypatch
):
    """A dead Valkey must not break the submission itself."""

    def boom():
        raise redis.RedisError("valkey down")

    monkeypatch.setattr(pyodide_support, "_get_valkey_client", boom)

    response = client.post(
        "/user/submit-agent-result",
        json=make_payload(
            execution_source="pyodide_fallback",
            fallback_reason="boot-timeout",
        ),
        headers=fallback_headers,
    )
    assert response.status_code == 200
