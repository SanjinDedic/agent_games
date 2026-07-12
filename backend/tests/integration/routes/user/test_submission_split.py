"""Tests pinning the Submission / SubmissionMetadata split invariants:
- save_submission creates a linked metadata + code pair and returns the code-row id
- record_failed_submission creates metadata only
- allow_submission counts failed attempts toward the rate limit
- hint_available sees failed attempts (cooldown + submissions-between-hints)
"""

from datetime import timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import (
    Institution,
    League,
    Submission,
    SubmissionMetadata,
    Team,
    TeamType,
)
from backend.routes.ai.hint_service import (
    HINT_COOLDOWN,
    SUBMISSIONS_BETWEEN_HINTS,
    hint_available,
)
from backend.routes.user.user_db import (
    SubmissionLimitExceededError,
    allow_submission,
    record_failed_submission,
    save_submission,
)
from backend.tests.conftest import add_failed_submission, add_submission
from backend.time_utils import utc_now



@pytest.fixture
def team(db_session: Session) -> Team:
    institution = db_session.exec(
        select(Institution).where(Institution.name == "Admin Institution")
    ).first()

    league = League(
        name="split_test_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)

    team = Team(
        name="split_test_team",
        school_name="Split School",
        password_hash="hash",
        league_id=league.id,
        institution_id=institution.id,
        team_type=TeamType.STUDENT,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def test_save_submission_creates_linked_pair(db_session: Session, team: Team):
    submission_id = save_submission(
        db_session,
        "# code",
        team.id,
        league_id=team.league_id,
        duration_ms=12.5,
        ranking=2,
    )

    sub = db_session.get(Submission, submission_id)
    assert sub is not None
    assert sub.code == "# code"
    assert sub.ranking == 2

    meta = db_session.get(SubmissionMetadata, sub.metadata_id)
    assert meta is not None
    assert meta.team_id == team.id
    assert meta.league_id == team.league_id
    assert meta.duration_ms == 12.5
    assert meta.timestamp == sub.timestamp


def test_record_failed_submission_stores_metadata_only(db_session: Session, team: Team):
    meta_id = record_failed_submission(
        db_session, team.id, league_id=team.league_id, duration_ms=3.0
    )

    meta = db_session.get(SubmissionMetadata, meta_id)
    assert meta is not None
    assert meta.team_id == team.id

    code_rows = db_session.exec(
        select(Submission).where(Submission.metadata_id == meta_id)
    ).all()
    assert code_rows == []


def test_allow_submission_counts_failed_attempts(db_session: Session, team: Team):
    now = utc_now()
    for _ in range(5):
        add_failed_submission(db_session, timestamp=now, team_id=team.id)
    db_session.commit()

    with pytest.raises(SubmissionLimitExceededError):
        allow_submission(db_session, team.id)


def test_hint_available_false_without_submissions(db_session: Session, team: Team):
    assert hint_available(db_session, team) is False


def test_hint_available_counts_failed_attempts(db_session: Session, team: Team):
    """Failed attempts count toward SUBMISSIONS_BETWEEN_HINTS just like passes."""
    base = utc_now() - timedelta(seconds=HINT_COOLDOWN + 60)
    for i in range(SUBMISSIONS_BETWEEN_HINTS - 1):
        add_failed_submission(
            db_session, timestamp=base + timedelta(seconds=i), team_id=team.id
        )
    add_submission(
        db_session,
        code="# ok",
        timestamp=base + timedelta(seconds=SUBMISSIONS_BETWEEN_HINTS),
        team_id=team.id,
    )
    db_session.commit()

    assert hint_available(db_session, team) is True


def test_hint_available_respects_cooldown(db_session: Session, team: Team):
    """Enough attempts but the first one is inside the cooldown window."""
    now = utc_now()
    for i in range(SUBMISSIONS_BETWEEN_HINTS):
        add_failed_submission(
            db_session, timestamp=now - timedelta(seconds=i), team_id=team.id
        )
    db_session.commit()

    assert hint_available(db_session, team) is False


def test_hint_available_requires_submissions_since_last_hint(
    db_session: Session, team: Team
):
    """After a hint, SUBMISSIONS_BETWEEN_HINTS more attempts are required."""
    base = utc_now() - timedelta(seconds=HINT_COOLDOWN + 60)
    add_submission(
        db_session,
        code="# hinted",
        timestamp=base,
        team_id=team.id,
        hint_included=True,
    )
    add_failed_submission(
        db_session, timestamp=base + timedelta(seconds=1), team_id=team.id
    )
    db_session.commit()

    # Only 1 attempt after the hinted one (indices: hinted=0, next=2 < 0+3)
    assert hint_available(db_session, team) is False

    for i in range(2, SUBMISSIONS_BETWEEN_HINTS + 1):
        add_failed_submission(
            db_session, timestamp=base + timedelta(seconds=i), team_id=team.id
        )
    db_session.commit()

    assert hint_available(db_session, team) is True
