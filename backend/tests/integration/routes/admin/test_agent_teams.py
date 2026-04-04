"""Tests for agent team management — create_agent_team and create_api_key in admin_db.py."""

from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import (
    AgentAPIKey,
    Institution,
    League,
    LeagueType,
    Team,
    TeamType,
)
from backend.routes.admin.admin_db import create_agent_team, create_api_key
from backend.routes.admin.admin_models import CreateAgentTeam


@pytest.fixture
def agent_league(db_session: Session) -> dict:
    """Create an institution with an agent-type league."""
    institution = db_session.exec(
        select(Institution).where(Institution.name == "Admin Institution")
    ).first()

    league = League(
        name="agent_test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=30),
        game="greedy_pig",
        league_type=LeagueType.AGENT,
        institution_id=institution.id,
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)

    return {"institution": institution, "league": league}


def test_create_agent_team_success(db_session, agent_league):
    """Creates an agent team in an agent league."""
    data = CreateAgentTeam(name="test_agent_team", league_id=agent_league["league"].id)
    result = create_agent_team(db_session, data)

    assert result["name"] == "test_agent_team"
    assert result["league"] == "agent_test_league"
    assert "team_id" in result

    team = db_session.get(Team, result["team_id"])
    assert team.team_type == TeamType.AGENT
    assert team.institution_id == agent_league["institution"].id


def test_create_agent_team_league_not_found(db_session):
    """Raises ValueError for non-existent league."""
    data = CreateAgentTeam(name="orphan_agent", league_id=99999)
    with pytest.raises(ValueError, match="not found"):
        create_agent_team(db_session, data)


def test_create_agent_team_wrong_league_type(db_session):
    """Raises ValueError when league is not an agent league."""
    institution = db_session.exec(
        select(Institution).where(Institution.name == "Admin Institution")
    ).first()

    student_league = League(
        name="student_league_for_agent_test",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        league_type=LeagueType.STUDENT,
        institution_id=institution.id,
    )
    db_session.add(student_league)
    db_session.commit()
    db_session.refresh(student_league)

    data = CreateAgentTeam(name="bad_agent", league_id=student_league.id)
    with pytest.raises(ValueError, match="agent leagues"):
        create_agent_team(db_session, data)


def test_create_api_key_success(db_session, agent_league):
    """Creates an API key for an agent team."""
    team_data = CreateAgentTeam(name="api_key_agent", league_id=agent_league["league"].id)
    team_result = create_agent_team(db_session, team_data)

    result = create_api_key(db_session, team_result["team_id"])
    assert "api_key" in result
    assert result["team_id"] == team_result["team_id"]
    assert len(result["api_key"]) > 20

    # Verify in DB
    key_record = db_session.exec(
        select(AgentAPIKey).where(AgentAPIKey.team_id == team_result["team_id"])
    ).first()
    assert key_record is not None


def test_create_api_key_team_not_found(db_session):
    """Raises ValueError for non-existent team."""
    with pytest.raises(ValueError, match="not found"):
        create_api_key(db_session, 99999)


def test_create_api_key_non_agent_team(db_session):
    """Raises ValueError when team is not an agent team."""
    institution = db_session.exec(
        select(Institution).where(Institution.name == "Admin Institution")
    ).first()
    unassigned = db_session.exec(
        select(League).where(League.name == "unassigned").where(League.institution_id == institution.id)
    ).first()

    student_team = Team(
        name="non_agent_team_for_key_test",
        school_name="School",
        password_hash="hash",
        league_id=unassigned.id,
        institution_id=institution.id,
        team_type=TeamType.STUDENT,
    )
    db_session.add(student_team)
    db_session.commit()
    db_session.refresh(student_team)

    with pytest.raises(ValueError, match="agent teams"):
        create_api_key(db_session, student_team.id)
