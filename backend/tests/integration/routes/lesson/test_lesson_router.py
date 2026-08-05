"""Student-facing lesson routes: read by slug. Snippet execution is
Pyodide-first in the browser with a direct browser→Lambda fallback — the
server never runs snippet code (the beacon endpoint is tested with the rest
of the fallback suite in backend/fallback_lambda/tests/)."""

import pytest
from sqlmodel import Session

from backend.database.db_models import Lesson

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
