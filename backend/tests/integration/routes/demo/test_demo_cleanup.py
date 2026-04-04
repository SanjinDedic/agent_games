"""Tests for demo cleanup functions and edge cases in demo_db.py."""

from datetime import datetime, timedelta

import pytest
import pytz
from sqlmodel import Session, select

from backend.database.db_models import (
    Institution,
    League,
    LeagueType,
    Submission,
    Team,
    TeamType,
    get_password_hash,
)
from backend.routes.demo.demo_db import (
    assign_user_to_demo_league,
    cleanup_expired_demo_users,
    cleanup_old_demo_submissions,
    get_or_create_demo_institution,
)

AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")


@pytest.fixture
def demo_setup(db_session: Session) -> dict:
    """Create demo infrastructure: institution, league, demo team with submissions."""
    now = datetime.now(AUSTRALIA_SYDNEY_TZ)

    demo_inst = get_or_create_demo_institution(db_session)
    db_session.commit()

    # Ensure unassigned league exists
    unassigned = db_session.exec(
        select(League).where(League.name == "unassigned")
    ).first()
    if not unassigned:
        unassigned = League(
            name="unassigned",
            created_date=now,
            expiry_date=now + timedelta(days=365),
            game="greedy_pig",
            institution_id=demo_inst.id,
            league_type=LeagueType.INSTITUTION,
        )
        db_session.add(unassigned)
        db_session.commit()
        db_session.refresh(unassigned)

    demo_league = League(
        name="greedy_pig_demo",
        created_date=now,
        expiry_date=now + timedelta(days=7),
        game="greedy_pig",
        league_type=LeagueType.STUDENT,
        is_demo=True,
        institution_id=demo_inst.id,
    )
    db_session.add(demo_league)
    db_session.commit()
    db_session.refresh(demo_league)

    # Old demo team (created 2 hours ago)
    old_team = Team(
        name="old_demo_team_Demo",
        school_name="old_demo",
        team_type=TeamType.STUDENT,
        is_demo=True,
        league_id=demo_league.id,
        created_at=now - timedelta(hours=2),
        password_hash=get_password_hash("pass"),
        institution_id=demo_inst.id,
    )
    db_session.add(old_team)
    db_session.commit()
    db_session.refresh(old_team)

    # Old submission
    old_sub = Submission(
        code="# old submission",
        timestamp=now - timedelta(hours=2),
        team_id=old_team.id,
    )
    db_session.add(old_sub)

    # Recent submission
    recent_sub = Submission(
        code="# recent submission",
        timestamp=now - timedelta(minutes=5),
        team_id=old_team.id,
    )
    db_session.add(recent_sub)
    db_session.commit()

    return {
        "demo_inst": demo_inst,
        "demo_league": demo_league,
        "unassigned": unassigned,
        "old_team": old_team,
    }


def test_cleanup_old_demo_submissions(db_session, demo_setup):
    """Deletes submissions older than the cutoff, keeps recent ones."""
    # Clean up submissions older than 60 minutes
    count = cleanup_old_demo_submissions(db_session, age_minutes=60)
    assert count >= 1

    # Recent submission should still exist
    remaining = db_session.exec(
        select(Submission).where(Submission.team_id == demo_setup["old_team"].id)
    ).all()
    assert len(remaining) >= 1
    assert any("recent" in s.code for s in remaining)


def test_cleanup_old_demo_submissions_no_teams(db_session):
    """Returns 0 when no demo teams exist (already cleaned up)."""
    # Delete all demo teams first
    demo_teams = db_session.exec(select(Team).where(Team.is_demo == True)).all()
    for t in demo_teams:
        db_session.exec(
            Submission.__table__.delete().where(Submission.team_id == t.id)
        )
        db_session.delete(t)
    db_session.commit()

    count = cleanup_old_demo_submissions(db_session, age_minutes=1)
    assert count == 0


def test_cleanup_expired_demo_users(db_session, demo_setup):
    """Deletes demo users older than the cutoff."""
    count = cleanup_expired_demo_users(db_session, age_minutes=60)
    assert count >= 1

    # The old team should be gone
    team = db_session.exec(
        select(Team).where(Team.name == "old_demo_team_Demo")
    ).first()
    assert team is None


def test_assign_user_to_demo_league_success(db_session, demo_setup):
    """Assigns a demo user to a demo league."""
    data = demo_setup
    result = assign_user_to_demo_league(db_session, data["old_team"].id, data["demo_league"].id)
    assert result is True

    db_session.refresh(data["old_team"])
    assert data["old_team"].league_id == data["demo_league"].id


def test_assign_user_to_demo_league_user_not_found(db_session, demo_setup):
    """Returns False when user doesn't exist."""
    result = assign_user_to_demo_league(db_session, 99999, demo_setup["demo_league"].id)
    assert result is False


def test_assign_user_to_demo_league_league_not_found(db_session, demo_setup):
    """Returns False when league doesn't exist."""
    result = assign_user_to_demo_league(db_session, demo_setup["old_team"].id, 99999)
    assert result is False
