"""Admin lesson CRUD: list, create, update, delete, and the slug rules."""

import pytest
from sqlmodel import Session

from backend.database.db_models import Lesson


@pytest.fixture
def existing_lesson(db_session: Session) -> Lesson:
    lesson = Lesson(
        slug="functions-basics",
        title="Functions explained",
        content="# Functions\n",
    )
    db_session.add(lesson)
    db_session.commit()
    db_session.refresh(lesson)
    return lesson


def test_list_lessons_is_admin_only(client, admin_headers, team_headers, existing_lesson):
    response = client.get("/lesson/lessons", headers=admin_headers)
    assert response.status_code == 200
    lessons = response.json()["lessons"]
    assert [lesson["slug"] for lesson in lessons] == ["functions-basics"]
    # Content stays out of the listing — the editor loads it by slug.
    assert "content" not in lessons[0]

    response = client.get("/lesson/lessons", headers=team_headers)
    assert response.status_code == 403


def test_create_lesson(client, admin_headers):
    response = client.post(
        "/lesson/lessons",
        headers=admin_headers,
        json={"slug": "new-lesson", "title": "New Lesson", "content": "# Hi\n"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "new-lesson"
    assert data["id"] is not None

    fetched = client.get("/lesson/lesson/new-lesson", headers=admin_headers)
    assert fetched.status_code == 200
    assert fetched.json()["content"] == "# Hi\n"


def test_create_lesson_requires_admin(client, team_headers):
    response = client.post(
        "/lesson/lessons",
        headers=team_headers,
        json={"slug": "x", "title": "X", "content": ""},
    )
    assert response.status_code == 403


def test_duplicate_slug_409s(client, admin_headers, existing_lesson):
    response = client.post(
        "/lesson/lessons",
        headers=admin_headers,
        json={"slug": "functions-basics", "title": "Other", "content": ""},
    )
    assert response.status_code == 409


@pytest.mark.parametrize(
    "bad_slug",
    ["Bad Slug", "UPPER", "trailing-", "-leading", "double--hyphen", "", "a" * 81],
)
def test_invalid_slug_422s(client, admin_headers, bad_slug):
    response = client.post(
        "/lesson/lessons",
        headers=admin_headers,
        json={"slug": bad_slug, "title": "T", "content": ""},
    )
    assert response.status_code == 422


def test_blank_title_422s(client, admin_headers):
    response = client.post(
        "/lesson/lessons",
        headers=admin_headers,
        json={"slug": "ok-slug", "title": "   ", "content": ""},
    )
    assert response.status_code == 422


def test_update_lesson(client, admin_headers, existing_lesson):
    response = client.put(
        f"/lesson/lesson/{existing_lesson.id}",
        headers=admin_headers,
        json={
            "slug": "functions-advanced",
            "title": "Functions, advanced",
            "content": "# More\n",
        },
    )
    assert response.status_code == 200
    assert response.json()["slug"] == "functions-advanced"

    # The old slug is gone, the new one resolves.
    assert (
        client.get(
            "/lesson/lesson/functions-basics", headers=admin_headers
        ).status_code
        == 404
    )
    fetched = client.get(
        "/lesson/lesson/functions-advanced", headers=admin_headers
    )
    assert fetched.json()["content"] == "# More\n"


def test_update_to_taken_slug_409s(client, admin_headers, existing_lesson):
    created = client.post(
        "/lesson/lessons",
        headers=admin_headers,
        json={"slug": "other-lesson", "title": "Other", "content": ""},
    ).json()
    response = client.put(
        f"/lesson/lesson/{created['id']}",
        headers=admin_headers,
        json={"slug": "functions-basics", "title": "Other", "content": ""},
    )
    assert response.status_code == 409

    # Keeping your own slug on update is not a collision.
    response = client.put(
        f"/lesson/lesson/{created['id']}",
        headers=admin_headers,
        json={"slug": "other-lesson", "title": "Renamed", "content": ""},
    )
    assert response.status_code == 200


def test_update_unknown_lesson_404s(client, admin_headers):
    response = client.put(
        "/lesson/lesson/99999",
        headers=admin_headers,
        json={"slug": "whatever", "title": "T", "content": ""},
    )
    assert response.status_code == 404


def test_delete_lesson(client, admin_headers, existing_lesson):
    response = client.delete(
        f"/lesson/lesson/{existing_lesson.id}", headers=admin_headers
    )
    assert response.status_code == 200
    assert (
        client.get(
            "/lesson/lesson/functions-basics", headers=admin_headers
        ).status_code
        == 404
    )


def test_delete_unknown_lesson_404s(client, admin_headers):
    response = client.delete("/lesson/lesson/99999", headers=admin_headers)
    assert response.status_code == 404
