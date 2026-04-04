"""Tests for GET /auth/institutions — public endpoint listing institution names."""

from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import Institution


@pytest.fixture
def multiple_institutions(db_session: Session) -> dict:
    """Create a mix of active, inactive, and demo institutions."""
    now = datetime.now()

    active = Institution(
        name="Active School",
        contact_person="Teacher",
        contact_email="teacher@school.com",
        created_date=now,
        subscription_active=True,
        subscription_expiry=now + timedelta(days=30),
        docker_access=True,
        password_hash="hash",
    )
    db_session.add(active)

    inactive = Institution(
        name="Inactive School",
        contact_person="Old Teacher",
        contact_email="old@school.com",
        created_date=now,
        subscription_active=False,
        subscription_expiry=now - timedelta(days=30),
        docker_access=True,
        password_hash="hash",
    )
    db_session.add(inactive)

    demo = Institution(
        name="Demo Institution",
        contact_person="Demo",
        contact_email="demo@example.com",
        created_date=now,
        subscription_active=True,
        subscription_expiry=now + timedelta(days=365),
        docker_access=True,
        password_hash="hash",
    )
    db_session.add(demo)

    db_session.commit()
    db_session.refresh(active)
    db_session.refresh(inactive)
    db_session.refresh(demo)

    return {"active": active, "inactive": inactive, "demo": demo}


def test_list_institutions_success(client, multiple_institutions):
    """Public endpoint returns only active, non-demo institutions."""
    resp = client.get("/auth/institutions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"

    names = data["data"]["institutions"]

    # Active institution is included
    assert "Active School" in names

    # Inactive institution is excluded
    assert "Inactive School" not in names

    # Demo Institution is excluded
    assert "Demo Institution" not in names

    # Admin Institution (created by conftest) is included since it's active
    assert "Admin Institution" in names


def test_list_institutions_no_auth_required(client, multiple_institutions):
    """Endpoint is public — no auth token needed."""
    resp = client.get("/auth/institutions")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_list_institutions_response_format(client, multiple_institutions):
    """Response has the expected structure."""
    resp = client.get("/auth/institutions")
    data = resp.json()
    assert "data" in data
    assert "institutions" in data["data"]
    assert isinstance(data["data"]["institutions"], list)
    # All items are strings
    for name in data["data"]["institutions"]:
        assert isinstance(name, str)
