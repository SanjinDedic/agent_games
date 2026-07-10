"""Integration test: only validated agents reach a greedy_pig simulation.

Seven teams join a greedy_pig league: two valid strategies and five invalid
agents the validator rejects (recorded as a SubmissionMetadata attempt with NO
linked Submission code row). The test passes only if exactly the two valid
teams play against each other.

The five invalid agents fall into two groups, on purpose:

1. Security violations (unauthorized imports, unauthorized `eval`). These would
   *load and play fine in the simulator if they ever reached it* — the
   simulator's add_player runs exec() with no AST security check. So the ONLY
   thing keeping them out is that failed attempts never get a Submission code
   row, so get_latest_submissions_for_league cannot see them. These make the
   test sensitive to the write path: store failed code in Submission and these
   agents leak into the run and show up in total_points.

2. Runtime faults (infinite loop / timeout, divide-by-zero on construction).
   These are *also* caught downstream — the validator kills the runaway loop
   agent after its hard timeout and reports failure, and the simulator's
   add_player drops the div-by-zero agent when construction raises (the game
   swallows exceptions inside make_decision, so the fault must surface before
   the game loop). They don't exercise the filter, but they assert the whole
   pipeline rejects every flavor of bad agent.

NOTE: the infinite-loop agent is the slowest submission here — it waits out the
validator's hard timeout before the error comes back.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.database.db_models import League, Submission, SubmissionMetadata, Team
from backend.tests.conftest import make_student_token


# --- Agent code under test --------------------------------------------------

# Two valid greedy_pig strategies.
VALID_BANK_AT_20 = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 20:
            return "bank"
        return "continue"
"""

VALID_BANK_AFTER_3_ROLLS = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["roll_no"] >= 3:
            return "bank"
        return "continue"
"""

# Three agents the validator rejects at the AST stage. Each would otherwise be a
# perfectly loadable, playable greedy_pig player, so only the absence of a
# Submission code row can keep them out of the simulation.

# Unauthorized import (module-level).
INVALID_IMPORT_OS = """
from games.greedy_pig.player import Player
import os

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "continue"
"""

# Unauthorized from-import.
INVALID_IMPORT_FROM = """
from games.greedy_pig.player import Player
from socket import socket

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return "bank"
"""

# Unauthorized eval() call.
INVALID_EVAL = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return eval("'bank'")
"""

# Infinite loop: never returns. The validator kills the runaway child after its
# hard timeout and reports a validation failure.
INVALID_TIMEOUT = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        while True:
            pass
        return "bank"
"""

# Divides by zero on construction, so add_player can never build the agent and
# validation fails. (The game swallows exceptions raised inside make_decision,
# so the fault has to surface before the game loop to be caught.)
INVALID_DIVIDE_BY_ZERO = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def __init__(self):
        super().__init__()
        self.ratio = 1 / 0

    def make_decision(self, game_state):
        return "bank"
"""


@pytest.fixture
def greedy_pig_league(db_session: Session) -> League:
    """The greedy_pig league seeded by populate_test_database."""
    return db_session.exec(
        select(League).where(League.name == "greedy_pig_league")
    ).first()


def _make_team(db_session: Session, league: League, name: str) -> Team:
    team = Team(
        name=name,
        school_name="Invalid Agents Test School",
        password_hash="test_hash",
        league_id=league.id,
        institution_id=league.institution_id,
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def _submit(client: TestClient, team: Team, code: str):
    headers = {"Authorization": f"Bearer {make_student_token(team)}"}
    return client.post("/user/submit-agent", headers=headers, json={"code": code})


def test_only_validated_agents_reach_greedy_pig_simulation(
    client: TestClient,
    db_session: Session,
    auth_headers: dict,
    greedy_pig_league: League,
):
    assert greedy_pig_league is not None, "greedy_pig_league should be seeded"

    valid_teams = {
        "valid_bank_at_20": VALID_BANK_AT_20,
        "valid_bank_after_3": VALID_BANK_AFTER_3_ROLLS,
    }
    invalid_teams = {
        "invalid_import_os": INVALID_IMPORT_OS,
        "invalid_import_from": INVALID_IMPORT_FROM,
        "invalid_eval": INVALID_EVAL,
        "invalid_timeout": INVALID_TIMEOUT,
        "invalid_divide_by_zero": INVALID_DIVIDE_BY_ZERO,
    }

    # 1. Seven teams submit code through the real validator. Invalid agents are
    #    rejected: their attempt is recorded in SubmissionMetadata but no
    #    Submission code row is written.
    teams_by_name = {}
    for name, code in {**valid_teams, **invalid_teams}.items():
        team = _make_team(db_session, greedy_pig_league, name)
        teams_by_name[name] = team
        response = _submit(client, team, code)
        if name in valid_teams:
            assert (
                response.status_code == 200
            ), f"{name} should pass validation: {response.json()}"
        else:
            assert (
                response.status_code == 400
            ), f"{name} should fail validation: {response.json()}"

    # 1b. DB-level invariants of the split write path.
    for name, team in teams_by_name.items():
        attempts = db_session.exec(
            select(SubmissionMetadata).where(SubmissionMetadata.team_id == team.id)
        ).all()
        code_rows = db_session.exec(
            select(Submission)
            .join(SubmissionMetadata, Submission.metadata_id == SubmissionMetadata.id)
            .where(SubmissionMetadata.team_id == team.id)
        ).all()
        if name in valid_teams:
            assert len(attempts) == 1, f"{name}: expected one recorded attempt"
            assert len(code_rows) == 1, f"{name}: expected one stored code row"
        else:
            assert len(attempts) == 1, f"{name}: failed attempt should be recorded"
            assert len(code_rows) == 0, f"{name}: failed code must NOT be stored"

    # 2. Run the simulation as admin (Admin Institution owns the seeded league).
    sim_response = client.post(
        "/institution/run-simulation",
        headers=auth_headers,
        json={"league_id": greedy_pig_league.id, "num_simulations": 20},
    )
    assert sim_response.status_code == 200, sim_response.text
    sim_data = sim_response.json()

    # 3. Only the two validated teams should have played. If failed code ever
    #    gets a Submission row again, the rejected agents (which load and
    #    play fine) leak in and this assertion fails.
    total_points = sim_data["total_points"]
    assert set(total_points.keys()) == set(valid_teams), (
        f"Only validated teams should reach the simulation, got: {set(total_points.keys())}"
    )
    for invalid_name in invalid_teams:
        assert invalid_name not in total_points
