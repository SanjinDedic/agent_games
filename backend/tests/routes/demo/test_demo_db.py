from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from backend.config import DEMO_TOKEN_EXPIRY
from backend.database.db_models import DemoUser, League, Team
from backend.routes.demo.demo_db import (
    assign_user_to_demo_league,
    create_demo_user,
    ensure_demo_leagues_exist,
    get_or_create_demo_league,
    save_demo_user_info,
)


def test_create_demo_user(db_session: Session):
    """Test creation of demo user"""
    team = create_demo_user(db_session, "TestUser")
    assert team is not None
    assert team.name == "TestUser_Demo"
    assert team.is_demo is True

    # Verify DemoUser record was created
    demo_user = db_session.exec(
        select(DemoUser).where(DemoUser.username == "TestUser")
    ).first()
    assert demo_user is not None


def test_save_demo_user_info(db_session: Session):
    """Test saving demo user info"""
    save_demo_user_info(db_session, "TestUser", "test@example.com")

    # Verify record was created
    demo_user = db_session.exec(
        select(DemoUser).where(DemoUser.username == "TestUser")
    ).first()
    assert demo_user is not None
    assert demo_user.email == "test@example.com"
    assert demo_user.created_at is not None


def test_get_or_create_demo_league(db_session: Session):
    """Test getting or creating demo league"""
    # First call should create league
    league1 = get_or_create_demo_league(db_session, "test_game")
    assert league1 is not None
    assert league1.name == "test_game_demo"
    assert league1.is_demo is True

    # Second call should return existing league
    league2 = get_or_create_demo_league(db_session, "test_game")
    assert league2 is not None
    assert league2.id == league1.id


def test_ensure_demo_leagues_exist(db_session: Session):
    """Test ensuring demo leagues exist for all games"""
    # Should create leagues for all games
    leagues = ensure_demo_leagues_exist(db_session)
    assert len(leagues) > 0

    # Verify all are demo leagues
    for league in leagues:
        assert league.is_demo is True
        assert league.name.endswith("_demo")


def test_assign_user_to_demo_league(db_session: Session):
    """Test assigning user to demo league"""
    # Create user and league
    team = create_demo_user(db_session, "LeagueAssignUser")
    league = get_or_create_demo_league(db_session, "test_game")

    # Assign user to league
    result = assign_user_to_demo_league(db_session, team.id, league.id)
    assert result is True

    # Verify assignment
    db_session.refresh(team)
    assert team.league_id == league.id


def test_create_demo_user_with_existing_team(db_session: Session):
    """Test creating a demo user when a team with similar name already exists"""
    # First create a demo user
    team1 = create_demo_user(db_session, "ExistingUser")

    # Try to create another with the same base name
    team2 = create_demo_user(db_session, "ExistingUser")

    # Should succeed and regenerate password for existing user
    assert team2 is not None
    assert team2.id == team1.id


def test_demo_user_creation_edge_cases(db_session: Session):
    """Test edge cases in demo user creation"""
    # Test with empty username
    team = create_demo_user(db_session, "")
    assert team is not None
    assert "Demo" in team.name

    # Test with very long username
    long_name = "A" * 30
    team = create_demo_user(db_session, long_name)
    assert team is not None
    assert len(team.name) <= 30  # DB field length constraint

    # Test with special characters
    special_name = "User!@#$%^&*()"
    team = create_demo_user(db_session, special_name)
    assert team is not None
    assert "User" in team.name
    assert "Demo" in team.name
