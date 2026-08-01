"""Student-facing lesson routes: read by slug, and run-snippet through the
real fallback runner (backend/fallback_lambda/, local subprocess mode in
tests)."""

import pytest
import redis
from sqlmodel import Session

import backend.routes.tutorial.pyodide_support as pyodide_support
from backend.database.db_models import Lesson
from backend.routes.lesson import lesson_db
from backend.tests.integration.routes.tutorial.test_pyodide_fallback import (  # noqa: F401 - fixture
    valkey,
)
from backend.time_utils import utc_now

LESSON_CONTENT = (
    "# Loops\n\n"
    "```python-run\nfor i in range(3):\n    print(i)\n```\n"
)


@pytest.fixture
def loops_lesson(db_session: Session) -> Lesson:
    lesson = Lesson(
        slug="loops-basics",
        title="Loops explained",
        content=LESSON_CONTENT,
    )
    db_session.add(lesson)
    db_session.commit()
    db_session.refresh(lesson)
    return lesson


@pytest.fixture(autouse=True)
def reset_snippet_rate_limit():
    """Snippet budgets live in Valkey with a 60s window, so counts leak
    across tests (and test runs) unless cleared."""
    try:
        client = lesson_db._get_rate_limit_client()
        keys = list(client.scan_iter("lesson-snippet-rate:*"))
        if keys:
            client.delete(*keys)
    except Exception:  # noqa: BLE001 - valkey down fails the run tests anyway
        pass
    yield


def test_get_lesson_by_slug(client, team_headers, loops_lesson):
    response = client.get("/lesson/lesson/loops-basics", headers=team_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "loops-basics"
    assert data["title"] == "Loops explained"
    assert data["content"] == LESSON_CONTENT

    # Unauthenticated access is rejected
    response = client.get("/lesson/lesson/loops-basics")
    assert response.status_code == 401


def test_get_unknown_lesson_404s(client, team_headers):
    response = client.get("/lesson/lesson/no-such-lesson", headers=team_headers)
    assert response.status_code == 404


def test_admin_can_read_lesson_by_slug(client, admin_headers, loops_lesson):
    response = client.get("/lesson/lesson/loops-basics", headers=admin_headers)
    assert response.status_code == 200


def test_run_snippet_returns_stdout(client, team_headers):
    response = client.post(
        "/lesson/run-snippet",
        headers=team_headers,
        json={"code": "print(sum(range(10)))"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["stdout"] == "45\n"
    assert data["traceback"] is None
    assert data["duration_ms"] is not None


def test_run_snippet_error_returns_traceback(
    client, team_headers
):
    """A crash is still a 200 — the traceback is the learning content."""
    response = client.post(
        "/lesson/run-snippet",
        headers=team_headers,
        json={"code": "print('before')\n1/0"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "ZeroDivisionError" in data["traceback"]
    assert data["stdout"] == "before\n"


def test_run_snippet_timeout(client, team_headers):
    response = client.post(
        "/lesson/run-snippet",
        headers=team_headers,
        json={"code": "while True: pass"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "did not finish" in data["message"]


def test_run_snippet_blank_code_422(client, team_headers):
    response = client.post(
        "/lesson/run-snippet", headers=team_headers, json={"code": "   "}
    )
    assert response.status_code == 422


def test_run_snippet_rate_limit(
    client, team_headers, monkeypatch
):
    """The budget is per identity in Valkey; shrink it so the test stays
    fast, and confirm the reused SubmissionLimitExceededError maps to 429."""
    monkeypatch.setattr(lesson_db, "SNIPPET_RUNS_PER_MINUTE", 2)
    for _ in range(2):
        response = client.post(
            "/lesson/run-snippet", headers=team_headers, json={"code": "x = 1"}
        )
        assert response.status_code == 200
    response = client.post(
        "/lesson/run-snippet", headers=team_headers, json={"code": "x = 1"}
    )
    assert response.status_code == 429


def test_run_snippet_requires_auth(client):
    response = client.post("/lesson/run-snippet", json={"code": "x = 1"})
    assert response.status_code == 401


def _today() -> str:
    return utc_now().strftime("%Y-%m-%d")


def test_run_snippet_fallback_is_counted(
    client, team_headers, valkey  # noqa: F811 - fixture
):
    """A Pyodide fallback run is a normal snippet run plus telemetry, with
    the reason prefixed "snippet:" in the counters shared with exercises."""
    response = client.post(
        "/lesson/run-snippet",
        headers=team_headers,
        json={
            "code": "print('hi')",
            "execution_source": "pyodide_fallback",
            "fallback_reason": "boot-timeout",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["stdout"] == "hi\n"

    assert valkey.get(f"pyodide-fallback:count:{_today()}") == "1"
    assert valkey.hgetall(f"pyodide-fallback:reasons:{_today()}") == {
        "snippet:boot-timeout": "1"
    }
    assert valkey.ttl(f"pyodide-fallback:count:{_today()}") > 0


def test_run_snippet_default_is_not_counted(
    client, team_headers, valkey  # noqa: F811 - fixture
):
    """The pre-existing default path must stay byte-identical: no counting."""
    response = client.post(
        "/lesson/run-snippet", headers=team_headers, json={"code": "x = 1"}
    )
    assert response.status_code == 200
    assert valkey.get(f"pyodide-fallback:count:{_today()}") is None


def test_run_snippet_fallback_telemetry_fails_open(
    client, team_headers, monkeypatch
):
    """A broken telemetry store must not break the run itself. (Only the
    telemetry client is patched — the rate limiter uses lesson_db's own.)"""

    def broken_client():
        raise redis.RedisError("valkey down")

    monkeypatch.setattr(pyodide_support, "_get_valkey_client", broken_client)
    response = client.post(
        "/lesson/run-snippet",
        headers=team_headers,
        json={
            "code": "print('hi')",
            "execution_source": "pyodide_fallback",
            "fallback_reason": "boot-timeout",
        },
    )
    assert response.status_code == 200
    assert response.json()["stdout"] == "hi\n"


def test_rate_limited_fallback_is_not_counted(
    client, team_headers, valkey, monkeypatch  # noqa: F811 - fixture
):
    """Telemetry is recorded after the rate limit, so spamming tagged
    requests can't inflate the fallback counters."""
    monkeypatch.setattr(lesson_db, "SNIPPET_RUNS_PER_MINUTE", 0)
    response = client.post(
        "/lesson/run-snippet",
        headers=team_headers,
        json={
            "code": "x = 1",
            "execution_source": "pyodide_fallback",
            "fallback_reason": "boot-timeout",
        },
    )
    assert response.status_code == 429
    assert valkey.get(f"pyodide-fallback:count:{_today()}") is None


def test_run_snippet_rejects_unknown_execution_source(client, team_headers):
    response = client.post(
        "/lesson/run-snippet",
        headers=team_headers,
        json={"code": "x = 1", "execution_source": "made-up"},
    )
    assert response.status_code == 422
