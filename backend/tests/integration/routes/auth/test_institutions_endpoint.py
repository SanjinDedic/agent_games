"""Tests for GET /auth/institutions — public endpoint listing institution names."""

from datetime import timedelta

import pytest
from sqlmodel import Session, select

from backend.tests.conftest import build_institution
from backend.database.db_models import Institution
from backend.time_utils import utc_now


@pytest.fixture
def multiple_institutions(db_session: Session) -> dict:
    """Create a mix of active, inactive, and demo institutions."""
    now = utc_now()

    active = build_institution(
        name="Active School",
        contact_person="Teacher",
        contact_email="teacher@school.com",
        created_date=now,
        subscription_active=True,
        subscription_expiry=now + timedelta(days=30),
        password_hash="hash",
    )
    db_session.add(active)

    inactive = build_institution(
        name="Inactive School",
        contact_person="Old Teacher",
        contact_email="old@school.com",
        created_date=now,
        subscription_active=False,
        subscription_expiry=now - timedelta(days=30),
        password_hash="hash",
    )
    db_session.add(inactive)

    demo = build_institution(
        name="Demo Institution",
        contact_person="Demo",
        contact_email="demo@example.com",
        created_date=now,
        subscription_active=True,
        subscription_expiry=now + timedelta(days=365),
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

    names = data["institutions"]

    # Active institution is included
    assert "Active School" in names

    # Inactive institution is excluded
    assert "Inactive School" not in names

    # Demo Institution is excluded
    assert "Demo Institution" not in names

    # Admin Institution (created by conftest) is included since it's active
    assert "Admin Institution" in names
