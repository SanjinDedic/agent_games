"""Tests for scheduled DB maintenance (backend/database/maintenance.py)."""

from datetime import timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import (
    Institution,
    League,
    LeagueType,
    Submission,
    SubmissionMetadata,
    Team,
    TeamType,
)
from backend.database.maintenance import (
    cleanup_agent_submissions,
    cleanup_institution_submissions,
)
from backend.tests.conftest import add_submission
from backend.time_utils import utc_now


def _get_or_create_institution(session: Session, name: str) -> Institution:
    inst = session.exec(select(Institution).where(Institution.name == name)).first()
    if not inst:
        inst = Institution(
            name=name,
            contact_person=name,
            contact_email=f"{name.replace(' ', '_').lower()}@test.com",
            created_date=utc_now(),
            password_hash="x",
        )
        session.add(inst)
        session.commit()
        session.refresh(inst)
    return inst


def _make_team(
    session: Session,
    name: str,
    institution: Institution,
    team_type: TeamType = TeamType.STUDENT,
) -> Team:
    now = utc_now()
    league = League(
        name=f"{name}_league",
        created_date=now,
        expiry_date=now + timedelta(days=7),
        game="greedy_pig",
        league_type=LeagueType.INSTITUTION,
        institution_id=institution.id,
    )
    session.add(league)
    session.commit()
    session.refresh(league)

    team = Team(
        name=name,
        school_name=name,
        league_id=league.id,
        institution_id=institution.id,
        team_type=team_type,
    )
    session.add(team)
    session.commit()
    session.refresh(team)
    return team


@pytest.fixture
def maintenance_setup(db_session: Session) -> dict:
    """Old + fresh submissions for a Demo Institution team, and an old
    submission for a regular institution team that must survive cleanup."""
    now = utc_now()

    demo_inst = _get_or_create_institution(db_session, "Demo Institution")
    other_inst = _get_or_create_institution(db_session, "Real School")

    demo_team = _make_team(db_session, "maint_demo_team", demo_inst)
    other_team = _make_team(db_session, "maint_other_team", other_inst)

    old_sub = add_submission(
        db_session, code="old", timestamp=now - timedelta(hours=25),
        team_id=demo_team.id, league_id=demo_team.league_id,
    )
    fresh_sub = add_submission(
        db_session, code="fresh", timestamp=now - timedelta(hours=1),
        team_id=demo_team.id, league_id=demo_team.league_id,
    )
    other_old_sub = add_submission(
        db_session, code="other_old", timestamp=now - timedelta(hours=48),
        team_id=other_team.id, league_id=other_team.league_id,
    )

    # Agent team in a regular institution: only the agent cleanup may touch it
    agent_team = _make_team(
        db_session, "maint_agent_team", other_inst, team_type=TeamType.AGENT
    )
    agent_old_sub = add_submission(
        db_session, code="agent_old", timestamp=now - timedelta(days=8),
        team_id=agent_team.id, league_id=agent_team.league_id,
    )
    agent_fresh_sub = add_submission(
        db_session, code="agent_fresh", timestamp=now - timedelta(days=1),
        team_id=agent_team.id, league_id=agent_team.league_id,
    )
    db_session.commit()

    return {
        "old_meta_id": old_sub.meta.id,
        "fresh_meta_id": fresh_sub.meta.id,
        "other_old_meta_id": other_old_sub.meta.id,
        "agent_old_meta_id": agent_old_sub.meta.id,
        "agent_fresh_meta_id": agent_fresh_sub.meta.id,
    }


def test_cleanup_deletes_only_old_target_institution_submissions(
    db_session: Session, maintenance_setup: dict
):
    """Old demo-institution submissions go; fresh ones and other institutions stay."""
    deleted = cleanup_institution_submissions(db_session, age_hours=24)

    assert deleted == 1

    remaining_meta_ids = {
        m.id for m in db_session.exec(select(SubmissionMetadata)).all()
    }
    assert maintenance_setup["old_meta_id"] not in remaining_meta_ids
    assert maintenance_setup["fresh_meta_id"] in remaining_meta_ids
    assert maintenance_setup["other_old_meta_id"] in remaining_meta_ids

    # The code row went with the metadata row
    orphan = db_session.exec(
        select(Submission).where(
            Submission.metadata_id == maintenance_setup["old_meta_id"]
        )
    ).first()
    assert orphan is None


def test_cleanup_noop_when_nothing_old(db_session: Session, maintenance_setup: dict):
    """A generous age window deletes nothing."""
    assert cleanup_institution_submissions(db_session, age_hours=72) == 0


def test_agent_cleanup_deletes_only_old_agent_submissions(
    db_session: Session, maintenance_setup: dict
):
    """8-day-old agent submissions go; 1-day-old agent ones and old
    student-team ones stay."""
    deleted = cleanup_agent_submissions(db_session, age_days=7)

    assert deleted == 1

    remaining_meta_ids = {
        m.id for m in db_session.exec(select(SubmissionMetadata)).all()
    }
    assert maintenance_setup["agent_old_meta_id"] not in remaining_meta_ids
    assert maintenance_setup["agent_fresh_meta_id"] in remaining_meta_ids
    # Student-team submissions are not the agent cleanup's business
    assert maintenance_setup["old_meta_id"] in remaining_meta_ids
    assert maintenance_setup["other_old_meta_id"] in remaining_meta_ids

    orphan = db_session.exec(
        select(Submission).where(
            Submission.metadata_id == maintenance_setup["agent_old_meta_id"]
        )
    ).first()
    assert orphan is None


def test_agent_cleanup_noop_when_nothing_old(
    db_session: Session, maintenance_setup: dict
):
    """A generous age window deletes nothing."""
    assert cleanup_agent_submissions(db_session, age_days=30) == 0
