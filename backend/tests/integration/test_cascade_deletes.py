"""Tests for ON DELETE CASCADE on the team and league child rows.

These cascades replaced a hand-written delete_team_children() that every delete
path had to remember to call. The failure mode they introduce is silent: if a
relationship lacks passive_deletes=True, SQLAlchemy pre-nulls the child's FK
before issuing the delete, so the database cascade never fires and the rows are
either orphaned or rejected by a NOT NULL constraint on a path no other test
covers.
"""

from datetime import timedelta

from sqlmodel import Session, select

from backend.database.db_models import (
    UNASSIGNED_LEAGUE_NAME,
    AgentAPIKey,
    League,
    SimulationResult,
    SimulationResultItem,
    Submission,
    SubmissionMetadata,
    Team,
    TeamType,
)
from backend.tests.conftest import add_submission
from backend.time_utils import utc_now


def _league(db_session: Session, name: str) -> League:
    league = League(
        name=name,
        created_date=utc_now(),
        expiry_date=utc_now() + timedelta(days=7),
        game="greedy_pig",
    )
    db_session.add(league)
    db_session.commit()
    db_session.refresh(league)
    return league


def _team(db_session: Session, name: str, league: League, agent: bool = False) -> Team:
    team = Team(
        name=name,
        school_name="Cascade School",
        password_hash="hash",
        league_id=league.id,
        team_type=TeamType.AGENT if agent else TeamType.STUDENT,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def test_deleting_a_team_removes_its_children(db_session: Session):
    """Submissions, attempt metadata, result rows and the API key all go."""
    league = _league(db_session, "cascade_team_league")
    team = _team(db_session, "cascade_team", league)

    add_submission(
        db_session, code="# code", timestamp=utc_now(), team_id=team.id,
        league_id=league.id,
    )
    db_session.add(AgentAPIKey(key="cascade-key", team_id=team.id))

    sim = SimulationResult(
        league_id=league.id, timestamp=utc_now(), num_simulations=1
    )
    db_session.add(sim)
    db_session.commit()
    db_session.refresh(sim)
    db_session.add(
        SimulationResultItem(simulation_result_id=sim.id, team_id=team.id, score=1.0)
    )
    db_session.commit()

    team_id = team.id
    db_session.delete(team)
    db_session.commit()

    assert db_session.get(Team, team_id) is None
    assert db_session.exec(
        select(SubmissionMetadata).where(SubmissionMetadata.team_id == team_id)
    ).all() == []
    assert db_session.exec(select(Submission)).all() == []
    assert db_session.exec(
        select(AgentAPIKey).where(AgentAPIKey.team_id == team_id)
    ).all() == []
    assert db_session.exec(
        select(SimulationResultItem).where(SimulationResultItem.team_id == team_id)
    ).all() == []


def test_deleting_a_league_removes_its_results(db_session: Session):
    """Simulation results cascade, and their items cascade in turn."""
    league = _league(db_session, "cascade_league")
    team = _team(db_session, "cascade_league_team", league)

    sim = SimulationResult(
        league_id=league.id, timestamp=utc_now(), num_simulations=3
    )
    db_session.add(sim)
    db_session.commit()
    db_session.refresh(sim)
    db_session.add(
        SimulationResultItem(simulation_result_id=sim.id, team_id=team.id, score=7.0)
    )
    db_session.commit()

    league_id, sim_id = league.id, sim.id
    # The team has to go first: it is the league's child too, and this test is
    # about the result rows.
    db_session.delete(team)
    db_session.commit()
    db_session.delete(db_session.get(League, league_id))
    db_session.commit()

    assert db_session.get(League, league_id) is None
    assert db_session.get(SimulationResult, sim_id) is None
    assert db_session.exec(
        select(SimulationResultItem).where(
            SimulationResultItem.simulation_result_id == sim_id
        )
    ).all() == []


def test_delete_league_endpoint_keeps_its_teams(client, owner_headers, db_session):
    """The endpoint reassigns teams before deleting, so the cascade must not
    take them. Without the reassignment, deleting a league would silently delete
    a whole class's accounts."""
    league = _league(db_session, "league_with_survivors")
    team = _team(db_session, "surviving_team", league)
    team_id = team.id

    response = client.post(
        "/owner/delete-league", headers=owner_headers, json={"league_id": league.id}
    )
    assert response.status_code == 200

    db_session.expire_all()
    survivor = db_session.get(Team, team_id)
    assert survivor is not None
    unassigned = db_session.exec(
        select(League).where(League.name == UNASSIGNED_LEAGUE_NAME)
    ).one()
    assert survivor.league_id == unassigned.id
