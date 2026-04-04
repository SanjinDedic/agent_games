"""Tests covering uncovered paths in user_db.py:
- allow_submission with non-existent team
- assign_team_to_league with demo user / non-demo league
- get_published_result with tz-naive dates and feedback_json
- get_all_published_results
- get_result_by_publish_link
- create_team_and_assign_to_league with non-existent league
"""

import json
import secrets
from datetime import datetime, timedelta

import pytest
import pytz
from sqlmodel import Session, select

from backend.database.db_models import (
    Institution,
    League,
    LeagueType,
    SimulationResult,
    SimulationResultItem,
    Submission,
    Team,
    TeamType,
)
from backend.routes.auth.auth_core import create_access_token
from backend.routes.user.user_db import (
    TeamNotFoundError,
    LeagueNotFoundError,
    TeamError,
    SubmissionLimitExceededError,
    allow_submission,
    assign_team_to_league,
    get_published_result,
    get_all_published_results,
    create_team_and_assign_to_league,
    get_result_by_publish_link,
)

AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")


@pytest.fixture
def published_league(db_session: Session) -> dict:
    """Create a league with a published simulation result including custom values and feedback."""
    institution = db_session.exec(
        select(Institution).where(Institution.name == "Admin Institution")
    ).first()

    league = League(
        name="published_test_league",
        created_date=datetime.now(),  # tz-naive on purpose to test localization
        expiry_date=datetime.now() + timedelta(days=7),  # tz-naive
        game="greedy_pig",
        institution_id=institution.id,
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)

    team = Team(
        name="published_test_team",
        school_name="School",
        password_hash="hash",
        league_id=league.id,
        institution_id=institution.id,
        team_type=TeamType.STUDENT,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    publish_link = secrets.token_urlsafe(16)
    sim = SimulationResult(
        league_id=league.id,
        timestamp=datetime.now(AUSTRALIA_SYDNEY_TZ),
        num_simulations=10,
        custom_rewards="[10, 8, 6]",
        published=True,
        publish_link=publish_link,
        feedback_json=json.dumps({"round_1": "Player banked early"}),
    )
    db_session.add(sim)
    db_session.commit()
    db_session.refresh(sim)

    result_item = SimulationResultItem(
        simulation_result_id=sim.id,
        team_id=team.id,
        score=100,
        custom_value1=5,
        custom_value1_name="wins",
    )
    db_session.add(result_item)
    db_session.commit()

    return {
        "league": league,
        "team": team,
        "sim": sim,
        "publish_link": publish_link,
        "institution": institution,
    }


def test_allow_submission_team_not_found(db_session):
    """allow_submission raises TeamNotFoundError for non-existent team."""
    with pytest.raises(TeamNotFoundError):
        allow_submission(db_session, 99999)


def test_assign_team_demo_to_non_demo_league(db_session):
    """Demo team cannot be assigned to a non-demo league."""
    institution = db_session.exec(
        select(Institution).where(Institution.name == "Admin Institution")
    ).first()

    league = League(
        name="non_demo_league_test",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
        is_demo=False,
    )
    db_session.add(league)
    db_session.commit()

    demo_team = Team(
        name="demo_assign_test",
        school_name="Demo",
        password_hash="hash",
        league_id=league.id,
        institution_id=institution.id,
        team_type=TeamType.STUDENT,
        is_demo=True,
    )
    db_session.add(demo_team)
    db_session.commit()

    with pytest.raises(ValueError, match="Demo users can only join demo leagues"):
        assign_team_to_league(db_session, "demo_assign_test", "non_demo_league_test")


def test_assign_team_not_found(db_session):
    """assign_team_to_league raises TeamNotFoundError for non-existent team."""
    institution = db_session.exec(
        select(Institution).where(Institution.name == "Admin Institution")
    ).first()
    league = League(
        name="assign_target_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
    )
    db_session.add(league)
    db_session.commit()

    with pytest.raises(TeamNotFoundError):
        assign_team_to_league(db_session, "nonexistent_team_xyz", "assign_target_league")


def test_get_published_result_with_feedback_json(db_session, published_league):
    """get_published_result returns feedback from feedback_json when feedback_str is None."""
    result = get_published_result(db_session, "published_test_league")
    assert result is not None
    assert result["league_name"] == "published_test_league"
    assert result["num_simulations"] == 10
    assert result["total_points"]["published_test_team"] == 100
    # feedback_json was set, feedback_str was None
    assert isinstance(result["feedback"], dict)
    assert "round_1" in result["feedback"]
    assert result["active"] is True


def test_get_published_result_no_published(db_session):
    """get_published_result returns None when no simulation is published."""
    institution = db_session.exec(
        select(Institution).where(Institution.name == "Admin Institution")
    ).first()
    league = League(
        name="no_published_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=7),
        game="greedy_pig",
        institution_id=institution.id,
    )
    db_session.add(league)
    db_session.commit()

    result = get_published_result(db_session, "no_published_league")
    assert result is None


def test_get_all_published_results(db_session, published_league):
    """get_all_published_results includes published results across leagues."""
    result = get_all_published_results(db_session)
    assert "all_results" in result
    # At least our published league should be in there
    league_names = [r.get("league_name") for r in result["all_results"]]
    assert "published_test_league" in league_names


def test_get_result_by_publish_link(db_session, published_league):
    """get_result_by_publish_link returns the correct published result."""
    result = get_result_by_publish_link(db_session, published_league["publish_link"])
    assert result["league_name"] == "published_test_league"
    assert "total_points" in result


def test_get_result_by_publish_link_not_found(db_session):
    """get_result_by_publish_link raises ValueError for invalid link."""
    with pytest.raises(ValueError, match="not found"):
        get_result_by_publish_link(db_session, "nonexistent_link_abc")


def test_create_team_and_assign_league_not_found(db_session):
    """create_team_and_assign_to_league raises when league doesn't exist."""
    with pytest.raises(LeagueNotFoundError):
        create_team_and_assign_to_league(db_session, "new_team", "pass", 99999)
