"""Direct-Lambda envelopes persisted through /tutorial/submit-exercise-result.

When the browser called the fallback Lambda's Function URL itself, the
persisted result arrives tagged execution_source="pyodide_fallback": the
submission then doubles as the fallback-telemetry beacon, the durable env
counter records "lambda", and stored rows are stamped "lambda_direct". The
untagged (local Pyodide) path must stay byte-identical.
"""

from sqlmodel import select

from backend.database.db_models import CodeEnvUsage, ExerciseSubmission
from backend.tests.integration.routes.tutorial.test_submit_exercise_result import (  # noqa: F401 - fixtures
    make_payload,
    make_row,
    pyodide_exercise,
)
from backend.time_utils import utc_now


def _today() -> str:
    return utc_now().strftime("%Y-%m-%d")


def test_direct_lambda_result_is_counted_and_stamped(
    client, db_session, team_headers, pyodide_exercise, valkey
):
    payload = make_payload(
        pyodide_exercise.id,
        execution_source="pyodide_fallback",
        fallback_reason="boot-timeout",
    )
    response = client.post(
        "/tutorial/submit-exercise-result", json=payload, headers=team_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is True
    assert all(row["source"] == "lambda_direct" for row in data["test_results"])

    # Stored rows carry the stamp too
    submission = db_session.exec(
        select(ExerciseSubmission).where(
            ExerciseSubmission.id == data["submission_id"]
        )
    ).one()
    assert submission.test_results == data["test_results"]

    # The submission doubled as the telemetry beacon
    assert valkey.get(f"pyodide-fallback:count:{_today()}") == "1"
    assert valkey.hgetall(f"pyodide-fallback:reasons:{_today()}") == {
        "boot-timeout": "1"
    }

    # And the durable env counter recorded a Lambda run, not a Pyodide one
    (usage,) = db_session.exec(select(CodeEnvUsage)).all()
    assert usage.kind == "exercise"
    assert usage.environment == "lambda"


def test_untagged_result_stays_pyodide(
    client, db_session, team_headers, pyodide_exercise, valkey
):
    response = client.post(
        "/tutorial/submit-exercise-result",
        json=make_payload(pyodide_exercise.id),
        headers=team_headers,
    )
    assert response.status_code == 200
    assert all(
        row["source"] == "pyodide"
        for row in response.json()["test_results"]
    )
    assert valkey.get(f"pyodide-fallback:count:{_today()}") is None
    (usage,) = db_session.exec(select(CodeEnvUsage)).all()
    assert usage.environment == "pyodide"
