"""Tests for GET /user/team-data — the student landing page's single fetch."""

from datetime import timedelta

import pytest
from sqlmodel import Session, select

from backend.database.db_models import (
    League,
    Submission,
    SubmissionMetadata,
    Team,
)
from backend.games.greedy_pig.validation_players import players as greedy_pig_bots
from backend.routes.auth.auth_db import mint_team_token

from backend.time_utils import utc_now

# Every league in these tests plays greedy_pig, so the validation field is
# always its bots plus the student.
GREEDY_PIG_FIELD_SIZE = len(greedy_pig_bots) + 1


@pytest.fixture
def classroom_fixture(db_session: Session) -> dict:
    """A league with one enrolled student and mixed agent progress."""
    now = utc_now()

    db_session.commit()

    league = League(
        name="team_data_classroom",
        created_date=now,
        expiry_date=now + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)

    team = Team(
        name="team_data_student",
        school_name="Team Data School",
        password_hash="hash",
        league_id=league.id,
    )
    db_session.add(team)

    db_session.commit()
    db_session.refresh(team)

    return {
        "league": league,
        "team": team,
    }


def _add_agent_attempt(
    db_session: Session,
    team_id: int,
    league_id: int,
    ranking: int | None = None,
    validated: bool = True,
) -> None:
    meta = SubmissionMetadata(
        team_id=team_id, league_id=league_id, timestamp=utc_now()
    )
    db_session.add(meta)
    db_session.flush()
    if validated:
        db_session.add(
            Submission(
                code="class CustomPlayer: pass",
                timestamp=utc_now(),
                ranking=ranking,
                metadata_id=meta.id,
            )
        )
    db_session.commit()


def test_team_data_classroom_full_payload(client, db_session, classroom_fixture):
    fix = classroom_fixture
    team = fix["team"]

    # Agent game: one failed validation, then ranked submissions 1st -> 3rd.
    _add_agent_attempt(db_session, team.id, fix["league"].id, validated=False)
    _add_agent_attempt(db_session, team.id, fix["league"].id, ranking=1)
    _add_agent_attempt(db_session, team.id, fix["league"].id, ranking=3)

    token = mint_team_token(team)
    resp = client.get(
        "/user/team-data", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, resp.json()
    data = resp.json()

    assert data["team_name"] == "team_data_student"
    assert data["league"] == {
        "id": fix["league"].id,
        "name": "team_data_classroom",
        "game": "greedy_pig",
    }

    agent = data["agent_game"]
    assert agent["total_attempts"] == 3
    assert agent["validated_submissions"] == 2
    assert agent["recent_rankings"] == [1, 3]  # oldest -> newest
    assert agent["best_ranking"] == 1
    assert agent["field_size"] == GREEDY_PIG_FIELD_SIZE
    assert agent["achieved_first"] is True
    assert agent["latest_submission"] is not None


def test_team_data_for_seed_team(client, db_session):
    """The payload shape for a team with no submissions yet."""
    league = db_session.exec(
        select(League).where(League.name == "greedy_pig_league")
    ).first()
    team = db_session.exec(select(Team).where(Team.name == "TeamA")).first()
    team.league_id = league.id
    db_session.commit()
    db_session.refresh(team)

    token = mint_team_token(team)
    resp = client.get(
        "/user/team-data", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["league"]["name"] == "greedy_pig_league"
    assert data["agent_game"]["total_attempts"] == 0
    assert data["agent_game"]["validated_submissions"] == 0
    assert data["agent_game"]["recent_rankings"] == []
    # Nothing ranked yet: no best placement, but the field is still sizeable.
    assert data["agent_game"]["best_ranking"] is None
    assert data["agent_game"]["field_size"] == GREEDY_PIG_FIELD_SIZE
    assert data["agent_game"]["achieved_first"] is False
    assert data["agent_game"]["latest_submission"] is None


def test_team_data_unassigned_team(client, db_session):
    """Unassigned teams get league=None so the frontend routes to the picker."""
    team = db_session.exec(select(Team).where(Team.name == "TeamB")).first()
    assert team.league.name == "unassigned"

    token = mint_team_token(team)
    resp = client.get(
        "/user/team-data", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["league"] is None
    assert data["agent_game"] is None


def test_team_data_stats_scoped_to_current_league(
    client, db_session, classroom_fixture
):
    """Attempts made in a previous league don't leak into the current one."""
    fix = classroom_fixture
    team = fix["team"]

    other_league = League(
        name="team_data_other_league",
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(other_league)
    db_session.commit()
    db_session.refresh(other_league)

    _add_agent_attempt(db_session, team.id, other_league.id, ranking=1)
    _add_agent_attempt(db_session, team.id, fix["league"].id, ranking=2)

    token = mint_team_token(team)
    resp = client.get(
        "/user/team-data", headers={"Authorization": f"Bearer {token}"}
    )
    agent = resp.json()["agent_game"]
    assert agent["total_attempts"] == 1
    assert agent["recent_rankings"] == [2]
    # The 1st place belongs to the other league and must not travel.
    assert agent["best_ranking"] == 2
    assert agent["achieved_first"] is False


def test_team_data_rejects_non_team_tokens(client, owner_headers):
    """Admin tokens fail the student-role gate before any team lookup."""
    resp = client.get("/user/team-data", headers=owner_headers)
    assert resp.status_code == 403


def test_team_data_requires_auth(client):
    resp = client.get("/user/team-data")
    assert resp.status_code in (401, 403)
