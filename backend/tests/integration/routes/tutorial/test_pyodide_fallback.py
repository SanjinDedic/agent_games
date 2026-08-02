"""Integration tests for the Pyodide-to-server fallback telemetry.

When the browser can't run Pyodide it submits through the normal server
path with execution_source="pyodide_fallback"; every such submission must be
counted (Valkey) and its stored rows stamped, while the default path stays
byte-identical to before the feature existed.
"""

import redis
from sqlmodel import select

import backend.routes.tutorial.pyodide_support as pyodide_support
from backend.database.db_models import ExerciseSubmission
from backend.tests.integration.routes.tutorial.test_tutorial_router import (  # noqa: F401 - fixtures
    PASSING_CODE,
    tutorial_with_exercise,
    word_counter_exercise,
)
from backend.time_utils import utc_now


def _today() -> str:
    return utc_now().strftime("%Y-%m-%d")


def test_fallback_submission_is_counted_and_stamped(
    client, db_session, team_headers, word_counter_exercise, valkey
):
    response = client.post(
        "/tutorial/submit-exercise",
        json={
            "exercise_id": word_counter_exercise.id,
            "code": PASSING_CODE,
            "execution_source": "pyodide_fallback",
            "fallback_reason": "boot-timeout",
        },
        headers=team_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is True
    assert all(
        row["source"] == "celery_fallback" for row in data["test_results"]
    )

    # Stored rows carry the stamp too (stored == echoed)
    submission = db_session.exec(
        select(ExerciseSubmission).where(
            ExerciseSubmission.id == data["submission_id"]
        )
    ).one()
    assert submission.test_results == data["test_results"]

    # Valkey counted the occurrence and the reason
    assert valkey.get(f"pyodide-fallback:count:{_today()}") == "1"
    assert valkey.hgetall(f"pyodide-fallback:reasons:{_today()}") == {
        "boot-timeout": "1"
    }
    assert valkey.ttl(f"pyodide-fallback:count:{_today()}") > 0


def test_default_submission_rows_are_untouched(
    client, db_session, team_headers, word_counter_exercise, valkey
):
    """The pre-existing default path must stay byte-identical: no source key
    in the rows, no fallback counting."""
    response = client.post(
        "/tutorial/submit-exercise",
        json={"exercise_id": word_counter_exercise.id, "code": PASSING_CODE},
        headers=team_headers,
    )
    assert response.status_code == 200
    for row in response.json()["test_results"]:
        assert "source" not in row
    assert valkey.get(f"pyodide-fallback:count:{_today()}") is None


def test_fallback_telemetry_failure_fails_open(
    client, team_headers, word_counter_exercise, monkeypatch
):
    """A dead Valkey must not break the submission itself."""

    def boom():
        raise redis.RedisError("valkey down")

    monkeypatch.setattr(pyodide_support, "_get_valkey_client", boom)

    response = client.post(
        "/tutorial/submit-exercise",
        json={
            "exercise_id": word_counter_exercise.id,
            "code": PASSING_CODE,
            "execution_source": "pyodide_fallback",
            "fallback_reason": "boot-fetch-failed",
        },
        headers=team_headers,
    )
    assert response.status_code == 200
    assert response.json()["passed"] is True


def test_preview_fallback_is_counted_but_not_persisted(
    client, db_session, institution_headers, word_counter_exercise, valkey
):
    response = client.post(
        "/tutorial/preview/submit-exercise",
        json={
            "exercise_id": word_counter_exercise.id,
            "code": PASSING_CODE,
            "execution_source": "pyodide_fallback",
            "fallback_reason": "worker-crashed",
        },
        headers=institution_headers,
    )
    assert response.status_code == 200
    assert response.json()["submission_id"] is None
    assert db_session.exec(select(ExerciseSubmission)).all() == []
    assert valkey.get(f"pyodide-fallback:count:{_today()}") == "1"


def test_admin_reads_fallback_stats(
    client, admin_headers, valkey
):
    valkey.incr(f"pyodide-fallback:count:{_today()}")
    valkey.incr(f"pyodide-fallback:count:{_today()}")
    valkey.hincrby(f"pyodide-fallback:reasons:{_today()}", "boot-timeout", 2)

    response = client.get("/diagnostics/pyodide-fallbacks", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["days"] == [
        {
            "date": _today(),
            "count": 2,
            "reasons": {"boot-timeout": 2},
        }
    ]

    # Students may not read diagnostics
    response = client.get("/diagnostics/pyodide-fallbacks")
    assert response.status_code == 401
