"""Tests for GET /auth/competitions — public endpoint listing competitions
(non-teacher institutions) for the student login picker."""

from datetime import timedelta

import pytest
from sqlmodel import Session

from backend.tests.conftest import build_institution
from backend.time_utils import utc_now


@pytest.fixture
def multiple_institutions(db_session: Session) -> dict:
    """Create a mix of competition, teacher, and demo institutions."""
    now = utc_now()

    competition = build_institution(
        name="Victorian Coding Challenge",
        contact_person="Organizer",
        contact_email="organizer@challenge.com",
        created_date=now,
        password_hash="hash",
        icon="🏆",
    )
    db_session.add(competition)

    teacher = build_institution(
        name="Ms Smith",
        contact_person="Ms Smith",
        contact_email="smith@school.com",
        created_date=now,
        password_hash="hash",
        is_teacher=True,
    )
    db_session.add(teacher)

    demo = build_institution(
        name="Demo Institution",
        contact_person="Demo",
        contact_email="demo@example.com",
        created_date=now,
        password_hash="hash",
    )
    db_session.add(demo)

    db_session.commit()

    return {
        "competition": competition,
        "teacher": teacher,
        "demo": demo,
    }


def test_list_competitions_success(client, multiple_institutions):
    """Public endpoint returns only non-teacher, non-demo institutions."""
    resp = client.get("/auth/competitions")
    assert resp.status_code == 200
    data = resp.json()

    by_name = {c["name"]: c for c in data["competitions"]}

    # Active competition is included, with its icon
    assert by_name["Victorian Coding Challenge"]["icon"] == "🏆"

    # Teacher accounts are excluded (classroom students use /join links)
    assert "Ms Smith" not in by_name

    # Demo Institution is excluded
    assert "Demo Institution" not in by_name

    # Admin Institution (created by conftest, non-teacher) is included;
    # no icon set, so it comes back null
    assert by_name["Admin Institution"]["icon"] is None
