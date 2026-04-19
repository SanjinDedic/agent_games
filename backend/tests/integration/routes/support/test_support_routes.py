"""Integration tests for /support endpoints — S3 side-effects are mocked."""

import io
from datetime import timedelta
from unittest.mock import patch

import pytest
from sqlmodel import select

from backend.database.db_models import SupportTicket, SupportTicketAttachment
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def team_headers() -> dict:
    token = create_access_token(
        data={"sub": "TeamA", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def institution_headers() -> dict:
    token = create_access_token(
        data={
            "sub": "Admin Institution",
            "role": "institution",
            "institution_id": 1,
        },
        expires_delta=timedelta(minutes=30),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers() -> dict:
    token = create_access_token(
        data={"sub": "admin", "role": "admin"},
        expires_delta=timedelta(minutes=30),
    )
    return {"Authorization": f"Bearer {token}"}


@patch("backend.routes.support.support_router.upload_attachment")
def test_team_can_submit_ticket(mock_upload, client, team_headers, db_session):
    mock_upload.return_value = "tickets/1/abc123_0"
    resp = client.post(
        "/support/create-ticket",
        headers=team_headers,
        data={
            "category": "bug",
            "subject": "Login broken",
            "description": "Cannot log in on Safari.",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert body["data"]["ticket_id"] > 0
    assert body["data"]["attachments"] == 0
    assert mock_upload.call_count == 0

    tickets = db_session.exec(select(SupportTicket)).all()
    assert len(tickets) == 1
    assert tickets[0].subject == "Login broken"
    assert tickets[0].submitter_type.value == "team"
    assert tickets[0].team_id is not None
    assert tickets[0].institution_id is None


@patch("backend.routes.support.support_router.upload_attachment")
def test_team_can_submit_ticket_with_attachments(
    mock_upload, client, team_headers, db_session
):
    mock_upload.side_effect = lambda *a, **k: f"tickets/1/{a[3]}"
    files = [
        ("files", ("a.png", io.BytesIO(b"\x89PNGfake1"), "image/png")),
        ("files", ("b.jpg", io.BytesIO(b"\xff\xd8fake2"), "image/jpeg")),
    ]
    resp = client.post(
        "/support/create-ticket",
        headers=team_headers,
        data={
            "category": "support",
            "subject": "Stuck on tutorial",
            "description": "Tutorial doesn't advance past step 3.",
        },
        files=files,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert body["data"]["attachments"] == 2
    assert mock_upload.call_count == 2

    attachments = db_session.exec(select(SupportTicketAttachment)).all()
    assert len(attachments) == 2
    assert {a.content_type for a in attachments} == {"image/png", "image/jpeg"}


def test_invalid_category_rejected(client, team_headers):
    resp = client.post(
        "/support/create-ticket",
        headers=team_headers,
        data={"category": "nonsense", "subject": "x", "description": "y"},
    )
    assert resp.status_code == 400


def test_empty_subject_rejected(client, team_headers):
    resp = client.post(
        "/support/create-ticket",
        headers=team_headers,
        data={"category": "bug", "subject": "   ", "description": "y"},
    )
    assert resp.status_code == 400


def test_empty_description_rejected(client, team_headers):
    resp = client.post(
        "/support/create-ticket",
        headers=team_headers,
        data={"category": "bug", "subject": "x", "description": ""},
    )
    # httpx may drop the empty field (422) before our Form(...) sees it, or our
    # validator returns 400 on whitespace-only input — both are acceptable rejections.
    assert resp.status_code in (400, 422)


def test_whitespace_description_rejected(client, team_headers):
    """Whitespace-only description bypasses FastAPI's Form empty-check and hits our validator."""
    resp = client.post(
        "/support/create-ticket",
        headers=team_headers,
        data={"category": "bug", "subject": "x", "description": "   "},
    )
    assert resp.status_code == 400
    assert "description" in resp.json()["detail"].lower()


def test_oversized_subject_rejected(client, team_headers):
    resp = client.post(
        "/support/create-ticket",
        headers=team_headers,
        data={"category": "bug", "subject": "x" * 500, "description": "y"},
    )
    assert resp.status_code == 400
    assert "subject" in resp.json()["detail"].lower()


def test_too_many_attachments_rejected(client, team_headers):
    files = [
        ("files", (f"{i}.png", io.BytesIO(b"\x89PNGfake"), "image/png"))
        for i in range(4)
    ]
    resp = client.post(
        "/support/create-ticket",
        headers=team_headers,
        data={"category": "bug", "subject": "x", "description": "y"},
        files=files,
    )
    assert resp.status_code == 400
    assert "attachments" in resp.json()["detail"].lower()


def test_oversized_attachment_rejected(client, team_headers):
    big = io.BytesIO(b"0" * (5 * 1024 * 1024 + 1))
    files = [("files", ("big.png", big, "image/png"))]
    resp = client.post(
        "/support/create-ticket",
        headers=team_headers,
        data={"category": "bug", "subject": "x", "description": "y"},
        files=files,
    )
    assert resp.status_code == 400
    assert "5 mb" in resp.json()["detail"].lower()


def test_disallowed_mime_rejected(client, team_headers):
    files = [("files", ("evil.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf"))]
    resp = client.post(
        "/support/create-ticket",
        headers=team_headers,
        data={"category": "bug", "subject": "x", "description": "y"},
        files=files,
    )
    assert resp.status_code == 400


@patch("backend.routes.support.support_router.upload_attachment")
def test_institution_can_submit_ticket(
    mock_upload, client, institution_headers, db_session
):
    resp = client.post(
        "/support/create-ticket",
        headers=institution_headers,
        data={
            "category": "feedback",
            "subject": "Love it",
            "description": "Works great for our class.",
        },
    )
    assert resp.status_code == 200, resp.text
    tickets = db_session.exec(select(SupportTicket)).all()
    assert len(tickets) == 1
    assert tickets[0].submitter_type.value == "institution"
    assert tickets[0].team_id is None
    assert tickets[0].institution_id is not None
    assert mock_upload.call_count == 0


def test_admin_cannot_submit_ticket(client, admin_headers):
    resp = client.post(
        "/support/create-ticket",
        headers=admin_headers,
        data={"category": "bug", "subject": "x", "description": "y"},
    )
    assert resp.status_code == 403


def test_no_auth_returns_401(client):
    resp = client.post(
        "/support/create-ticket",
        data={"category": "bug", "subject": "x", "description": "y"},
    )
    assert resp.status_code == 401


@patch("backend.routes.support.support_router.delete_attachment")
@patch("backend.routes.support.support_router.upload_attachment")
def test_s3_failure_rolls_back_and_cleans_up(
    mock_upload, mock_delete, client, team_headers, db_session
):
    """If the 2nd upload blows up we should roll back and best-effort delete the 1st."""
    from sqlmodel import select

    from backend.database.db_models import SupportTicket, SupportTicketAttachment

    def _upload(bytes_, ct, tid, idx, submitter_type):
        if idx == 0:
            return f"tickets/{tid}/ok_0"
        raise RuntimeError("s3 down")

    mock_upload.side_effect = _upload

    import io

    files = [
        ("files", ("a.png", io.BytesIO(b"\x89PNGfake1"), "image/png")),
        ("files", ("b.png", io.BytesIO(b"\x89PNGfake2"), "image/png")),
    ]
    resp = client.post(
        "/support/create-ticket",
        headers=team_headers,
        data={"category": "bug", "subject": "x", "description": "y"},
        files=files,
    )
    assert resp.status_code == 500

    # First S3 object was deleted by the rollback path
    mock_delete.assert_called_once_with("tickets/1/ok_0")

    # No ticket / attachment rows persisted
    assert db_session.exec(select(SupportTicket)).all() == []
    assert db_session.exec(select(SupportTicketAttachment)).all() == []


def test_unknown_team_returns_error(client, db_session):
    """Token refers to a team that no longer exists in the DB → friendly error."""
    from datetime import timedelta

    from backend.routes.auth.auth_core import create_access_token

    token = create_access_token(
        data={"sub": "GhostTeam", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    resp = client.post(
        "/support/create-ticket",
        headers={"Authorization": f"Bearer {token}"},
        data={"category": "bug", "subject": "x", "description": "y"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"
    assert "not found" in body["message"].lower()


def test_unknown_institution_returns_error(client):
    """Token refers to an institution not in the DB → friendly error."""
    from datetime import timedelta

    from backend.routes.auth.auth_core import create_access_token

    token = create_access_token(
        data={"sub": "Ghost Institute", "role": "institution"},
        expires_delta=timedelta(minutes=30),
    )
    resp = client.post(
        "/support/create-ticket",
        headers={"Authorization": f"Bearer {token}"},
        data={"category": "support", "subject": "x", "description": "y"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"
    assert "not found" in body["message"].lower()


def test_ai_agent_role_forbidden(client):
    """verify_non_admin allows ai_agent through the decorator, but the endpoint rejects it at role check."""
    from datetime import timedelta

    from backend.routes.auth.auth_core import create_access_token

    token = create_access_token(
        data={"sub": "bot", "role": "ai_agent"},
        expires_delta=timedelta(minutes=30),
    )
    resp = client.post(
        "/support/create-ticket",
        headers={"Authorization": f"Bearer {token}"},
        data={"category": "bug", "subject": "x", "description": "y"},
    )
    assert resp.status_code == 403


def test_empty_attachment_rejected(client, team_headers):
    import io

    files = [("files", ("empty.png", io.BytesIO(b""), "image/png"))]
    resp = client.post(
        "/support/create-ticket",
        headers=team_headers,
        data={"category": "bug", "subject": "x", "description": "y"},
        files=files,
    )
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()
