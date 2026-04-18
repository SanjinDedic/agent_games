"""Integration tests for the admin-side /admin/support-tickets endpoints."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlmodel import select

from backend.database.db_models import (
    Institution,
    SupportTicket,
    SupportTicketAttachment,
    SupportTicketCategory,
    SupportTicketStatus,
    SupportTicketSubmitterType,
    Team,
)
from backend.routes.auth.auth_core import create_access_token


@pytest.fixture
def admin_headers() -> dict:
    token = create_access_token(
        data={"sub": "admin", "role": "admin"},
        expires_delta=timedelta(minutes=30),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def student_headers() -> dict:
    token = create_access_token(
        data={"sub": "TeamA", "role": "student"},
        expires_delta=timedelta(minutes=30),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def patch_presign():
    """Avoid real S3/MinIO calls in admin-list tests."""
    with patch(
        "backend.routes.support.support_db.presign_attachment",
        return_value="http://presigned-url",
    ):
        yield


def _seed_tickets(db_session):
    team = db_session.exec(select(Team).where(Team.name == "TeamA")).first()
    institution = db_session.exec(
        select(Institution).where(Institution.name == "Admin Institution")
    ).first()

    now = datetime.utcnow()
    db_session.add(
        SupportTicket(
            category=SupportTicketCategory.BUG,
            subject="Team bug",
            description="Team bug description",
            status=SupportTicketStatus.OPEN,
            submitter_type=SupportTicketSubmitterType.TEAM,
            team_id=team.id,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        SupportTicket(
            category=SupportTicketCategory.FEEDBACK,
            subject="Institution feedback",
            description="Institution feedback description",
            status=SupportTicketStatus.RESOLVED,
            submitter_type=SupportTicketSubmitterType.INSTITUTION,
            institution_id=institution.id,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()


def test_list_all_tickets(client, admin_headers, db_session):
    _seed_tickets(db_session)
    resp = client.get("/admin/support-tickets?submitter_type=all", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert len(body["data"]["tickets"]) == 2


def test_invalid_submitter_type_returns_error(client, admin_headers):
    resp = client.get(
        "/admin/support-tickets?submitter_type=nope", headers=admin_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"
    assert "invalid submitter_type" in body["message"].lower()


def test_invalid_status_filter_returns_error(client, admin_headers):
    resp = client.get(
        "/admin/support-tickets?status=unknown", headers=admin_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"
    assert "invalid status" in body["message"].lower()


def test_list_with_presign_failure_returns_empty_url(
    client, admin_headers, db_session
):
    """If S3 presign fails, the ticket still loads with an empty URL string."""
    _seed_tickets(db_session)
    team_ticket = db_session.exec(
        select(SupportTicket).where(SupportTicket.subject == "Team bug")
    ).first()
    db_session.add(
        SupportTicketAttachment(
            ticket_id=team_ticket.id,
            s3_key="tickets/missing/file",
            content_type="image/png",
            size_bytes=10,
            original_filename="a.png",
        )
    )
    db_session.commit()

    with patch(
        "backend.routes.support.support_db.presign_attachment",
        side_effect=RuntimeError("minio unreachable"),
    ):
        resp = client.get(
            "/admin/support-tickets?submitter_type=team", headers=admin_headers
        )
    assert resp.status_code == 200
    tickets = resp.json()["data"]["tickets"]
    assert len(tickets) == 1
    assert tickets[0]["attachments"][0]["url"] == ""


def test_filter_by_team_submitter(client, admin_headers, db_session):
    _seed_tickets(db_session)
    resp = client.get("/admin/support-tickets?submitter_type=team", headers=admin_headers)
    assert resp.status_code == 200
    tickets = resp.json()["data"]["tickets"]
    assert len(tickets) == 1
    assert tickets[0]["submitter_type"] == "team"
    assert tickets[0]["submitter"]["name"] == "TeamA"


def test_filter_by_institution_submitter(client, admin_headers, db_session):
    _seed_tickets(db_session)
    resp = client.get(
        "/admin/support-tickets?submitter_type=institution", headers=admin_headers
    )
    assert resp.status_code == 200
    tickets = resp.json()["data"]["tickets"]
    assert len(tickets) == 1
    assert tickets[0]["submitter_type"] == "institution"
    assert tickets[0]["submitter"]["name"] == "Admin Institution"


def test_filter_by_status(client, admin_headers, db_session):
    _seed_tickets(db_session)
    resp = client.get(
        "/admin/support-tickets?submitter_type=all&status=resolved", headers=admin_headers
    )
    assert resp.status_code == 200
    tickets = resp.json()["data"]["tickets"]
    assert len(tickets) == 1
    assert tickets[0]["status"] == "resolved"


def test_list_requires_admin(client, student_headers):
    resp = client.get("/admin/support-tickets", headers=student_headers)
    assert resp.status_code == 403


def test_list_requires_auth(client):
    resp = client.get("/admin/support-tickets")
    assert resp.status_code == 401


def test_update_ticket_status_and_note(client, admin_headers, db_session):
    _seed_tickets(db_session)
    ticket = db_session.exec(select(SupportTicket)).first()

    resp = client.post(
        "/admin/support-ticket-update",
        headers=admin_headers,
        json={
            "ticket_id": ticket.id,
            "status": "in_progress",
            "admin_note": "Investigating",
        },
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()["data"]["ticket"]
    assert updated["status"] == "in_progress"
    assert updated["admin_note"] == "Investigating"


def test_update_requires_admin(client, student_headers, db_session):
    _seed_tickets(db_session)
    ticket = db_session.exec(select(SupportTicket)).first()

    resp = client.post(
        "/admin/support-ticket-update",
        headers=student_headers,
        json={"ticket_id": ticket.id, "status": "resolved"},
    )
    assert resp.status_code == 403


def test_update_missing_ticket_returns_error(client, admin_headers):
    resp = client.post(
        "/admin/support-ticket-update",
        headers=admin_headers,
        json={"ticket_id": 9999, "status": "resolved"},
    )
    assert resp.status_code == 200  # app returns ErrorResponseModel, not HTTP error
    body = resp.json()
    assert body["status"] == "error"
    assert "not found" in body["message"].lower()


def test_update_invalid_status(client, admin_headers, db_session):
    _seed_tickets(db_session)
    ticket = db_session.exec(select(SupportTicket)).first()

    resp = client.post(
        "/admin/support-ticket-update",
        headers=admin_headers,
        json={"ticket_id": ticket.id, "status": "nope"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"
    assert "invalid status" in body["message"].lower()


@patch("backend.routes.support.support_db.delete_attachment")
def test_delete_ticket_removes_row_and_attachments(
    mock_delete, client, admin_headers, db_session
):
    _seed_tickets(db_session)
    ticket = db_session.exec(
        select(SupportTicket).where(SupportTicket.subject == "Team bug")
    ).first()
    db_session.add(
        SupportTicketAttachment(
            ticket_id=ticket.id,
            s3_key="tickets/X/file",
            content_type="image/png",
            size_bytes=10,
            original_filename="a.png",
        )
    )
    db_session.commit()

    resp = client.delete(
        f"/admin/support-ticket/{ticket.id}", headers=admin_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert body["data"]["attachments_deleted"] == 1

    mock_delete.assert_called_once_with("tickets/X/file")
    assert db_session.get(SupportTicket, ticket.id) is None
    remaining_attachments = db_session.exec(
        select(SupportTicketAttachment).where(
            SupportTicketAttachment.ticket_id == ticket.id
        )
    ).all()
    assert remaining_attachments == []


def test_delete_missing_ticket_returns_error(client, admin_headers):
    resp = client.delete("/admin/support-ticket/9999", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"
    assert "not found" in body["message"].lower()


def test_delete_requires_admin(client, student_headers, db_session):
    _seed_tickets(db_session)
    ticket = db_session.exec(select(SupportTicket)).first()
    resp = client.delete(
        f"/admin/support-ticket/{ticket.id}", headers=student_headers
    )
    assert resp.status_code == 403


def test_delete_requires_auth(client, db_session):
    _seed_tickets(db_session)
    ticket = db_session.exec(select(SupportTicket)).first()
    resp = client.delete(f"/admin/support-ticket/{ticket.id}")
    assert resp.status_code == 401
