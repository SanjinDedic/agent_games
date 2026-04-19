"""Unit tests for team-name sanitization + counter logic."""

from datetime import datetime, timedelta

import pytest
import pytz
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from backend.database.db_models import (
    Institution,
    League,
    LeagueType,
    Team,
    TeamType,
)
from backend.routes.user.team_naming import (
    create_school_team,
    next_available_team_name,
    sanitize_school_name,
)

AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Willetton SHS", "WillettonSHS"),
        ("Willetton SHS!", "WillettonSHS"),
        ("   Willetton   SHS   ", "WillettonSHS"),
        ("St. Mary's College", "StMarysCollege"),
        ("", ""),
        ("!!!", ""),
        ("École", "cole"),  # documented: non-ASCII stripped
        ("School 7", "School7"),
    ],
)
def test_sanitize_school_name(raw, expected):
    assert sanitize_school_name(raw) == expected


def test_next_available_team_name_empty_db(db_session: Session):
    # Fresh DB has no Foo-prefixed teams
    assert next_available_team_name(db_session, "Foo") == "Foo1"


def test_next_available_team_name_with_gaps(db_session: Session):
    league = db_session.exec(select(League).where(League.name == "unassigned")).first()
    for n in (1, 3):
        db_session.add(
            Team(
                name=f"Foo{n}",
                school_name="Foo",
                password_hash="hash",
                league_id=league.id,
                team_type=TeamType.STUDENT,
            )
        )
    db_session.commit()

    # Skips 1, finds 2 (gap between 1 and 3)
    assert next_available_team_name(db_session, "Foo") == "Foo2"


def test_next_available_team_name_ignores_non_numeric_suffix(db_session: Session):
    """Teams like 'FooBar' must not confuse the counter."""
    league = db_session.exec(select(League).where(League.name == "unassigned")).first()
    db_session.add(
        Team(
            name="FooBar",
            school_name="Foo",
            password_hash="hash",
            league_id=league.id,
            team_type=TeamType.STUDENT,
        )
    )
    db_session.commit()
    assert next_available_team_name(db_session, "Foo") == "Foo1"


def test_next_available_team_name_empty_sanitized_raises(db_session: Session):
    with pytest.raises(ValueError):
        next_available_team_name(db_session, "")


def test_create_school_team_integrity_retry(db_session: Session, monkeypatch):
    """If the first commit hits IntegrityError, the counter advances and a second commit succeeds."""
    now = datetime.now(AUSTRALIA_SYDNEY_TZ)
    institution = db_session.exec(
        select(Institution).where(Institution.name == "Admin Institution")
    ).first()
    league = League(
        name="retry_test_league",
        created_date=now,
        expiry_date=now + timedelta(days=1),
        game="greedy_pig",
        institution_id=institution.id,
        league_type=LeagueType.INSTITUTION,
        school_league=True,
        schools_config={"source": "static", "schools": ["Willetton"]},
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)

    original_commit = Session.commit
    calls = {"n": 0}

    def flaky_commit(self):
        calls["n"] += 1
        if calls["n"] == 1:
            raise IntegrityError("simulated", None, Exception("race"))
        return original_commit(self)

    monkeypatch.setattr(Session, "commit", flaky_commit)

    team = create_school_team(db_session, league.id, "Willetton", "pw")
    assert team.name == "Willetton2"
    assert calls["n"] >= 2


def test_create_school_team_rejects_empty_sanitized(db_session: Session):
    league = db_session.exec(select(League).where(League.name == "unassigned")).first()
    with pytest.raises(ValueError):
        create_school_team(db_session, league.id, "!!!", "pw")
