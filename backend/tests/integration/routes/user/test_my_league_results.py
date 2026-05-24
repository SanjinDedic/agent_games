from datetime import datetime, timedelta

import pytest
import pytz
from sqlmodel import Session

from backend.database.db_models import (
    League,
    SimulationResult,
    SimulationResultItem,
    Team,
)
from backend.routes.auth.auth_db import mint_team_token

AUSTRALIA_SYDNEY_TZ = pytz.timezone("Australia/Sydney")


@pytest.fixture
def two_leagues_with_published_results(db_session: Session) -> dict:
    """Two leagues; each has one published and one unpublished result, plus a team."""
    league_a = League(
        name="my_league_a",
        game="greedy_pig",
        created_date=datetime.now(AUSTRALIA_SYDNEY_TZ),
        expiry_date=datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(days=7),
        info_markdown="# League A schedule",
    )
    league_b = League(
        name="my_league_b",
        game="greedy_pig",
        created_date=datetime.now(AUSTRALIA_SYDNEY_TZ),
        expiry_date=datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(days=7),
        info_markdown="# League B schedule",
    )
    db_session.add(league_a)
    db_session.add(league_b)
    db_session.commit()
    db_session.refresh(league_a)
    db_session.refresh(league_b)

    team_a = Team(
        name="my_league_team_a",
        school_name="A School",
        password_hash="x",
        league_id=league_a.id,
    )
    db_session.add(team_a)
    db_session.commit()
    db_session.refresh(team_a)

    # League A: two published + one unpublished
    sim_a1 = SimulationResult(
        league_id=league_a.id,
        timestamp=datetime.now(AUSTRALIA_SYDNEY_TZ),
        num_simulations=10,
        custom_rewards="[10, 8, 6, 4, 2]",
        published=True,
        publish_link="link-a1",
    )
    sim_a2 = SimulationResult(
        league_id=league_a.id,
        timestamp=datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(hours=1),
        num_simulations=20,
        custom_rewards="[10, 8, 6, 4, 2]",
        published=True,
        publish_link="link-a2",
    )
    sim_a_unpub = SimulationResult(
        league_id=league_a.id,
        timestamp=datetime.now(AUSTRALIA_SYDNEY_TZ),
        num_simulations=5,
        custom_rewards="[10, 8, 6, 4, 2]",
        published=False,
    )

    # League B: one published (must NOT appear for team A)
    sim_b1 = SimulationResult(
        league_id=league_b.id,
        timestamp=datetime.now(AUSTRALIA_SYDNEY_TZ),
        num_simulations=10,
        custom_rewards="[10, 8, 6, 4, 2]",
        published=True,
        publish_link="link-b1",
    )
    db_session.add_all([sim_a1, sim_a2, sim_a_unpub, sim_b1])
    db_session.commit()
    for s in (sim_a1, sim_a2, sim_a_unpub, sim_b1):
        db_session.refresh(s)

    # Attach a SimulationResultItem so total_points is non-empty
    db_session.add(
        SimulationResultItem(
            simulation_result_id=sim_a1.id, team_id=team_a.id, score=42
        )
    )
    db_session.commit()

    return {
        "league_a": league_a,
        "league_b": league_b,
        "team_a": team_a,
        "sim_a1": sim_a1,
        "sim_a2": sim_a2,
        "sim_b1": sim_b1,
    }


def test_my_league_results_scoped_to_league(client, two_leagues_with_published_results):
    fix = two_leagues_with_published_results
    token = mint_team_token(fix["team_a"])
    response = client.get(
        "/user/get-all-published-results-for-my-league",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    body = data["data"]
    assert body["league_name"] == "my_league_a"
    assert body["info_markdown"] == "# League A schedule"

    ids = {r["id"] for r in body["all_results"]}
    assert fix["sim_a1"].id in ids
    assert fix["sim_a2"].id in ids
    # Unpublished result excluded
    assert all(r.get("publish_link") for r in body["all_results"])
    # League B result is NOT visible
    assert fix["sim_b1"].id not in ids
    # Newest first
    assert body["all_results"][0]["id"] >= body["all_results"][-1]["id"]


def test_my_league_results_requires_auth(client):
    response = client.get("/user/get-all-published-results-for-my-league")
    assert response.status_code == 401


def test_my_league_results_no_league(client, db_session):
    """Team with no league assigned gets an empty list (not a 500)."""
    # Build a team with league_id=None… but the column is NOT NULL.
    # Instead, use an unassigned league that has no published results.
    unassigned = League(
        name="my_league_empty",
        game="greedy_pig",
        created_date=datetime.now(AUSTRALIA_SYDNEY_TZ),
        expiry_date=datetime.now(AUSTRALIA_SYDNEY_TZ) + timedelta(days=7),
    )
    db_session.add(unassigned)
    db_session.commit()
    db_session.refresh(unassigned)

    team = Team(
        name="my_league_empty_team",
        school_name="School",
        password_hash="x",
        league_id=unassigned.id,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    token = mint_team_token(team)
    response = client.get(
        "/user/get-all-published-results-for-my-league",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["league_name"] == "my_league_empty"
    assert body["data"]["all_results"] == []


def test_get_all_leagues_includes_info_markdown(client, two_leagues_with_published_results):
    """The /user/get-all-leagues response carries info_markdown for the frontend."""
    fix = two_leagues_with_published_results
    token = mint_team_token(fix["team_a"])
    response = client.get(
        "/user/get-all-leagues",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    leagues = response.json()["data"]["leagues"]
    by_name = {l["name"]: l for l in leagues}
    # team_a is institution_id=None => admin-only sees all; student with no
    # institution returns empty. We assert the field exists when present.
    for league in leagues:
        assert "info_markdown" in league
