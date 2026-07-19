"""Student-facing lesson routes: read by slug, and run-snippet through the
real broker and exercises worker (the celery_workers fixture fails fast when
the workers are down)."""

import pytest
from sqlmodel import Session

from backend.database.db_models import Lesson
from backend.routes.lesson import lesson_db

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


def test_run_snippet_returns_stdout(client, team_headers, celery_workers):
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
    client, team_headers, celery_workers
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


def test_run_snippet_timeout(client, team_headers, celery_workers):
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
    client, team_headers, celery_workers, monkeypatch
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
