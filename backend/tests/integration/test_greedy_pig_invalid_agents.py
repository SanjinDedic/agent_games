"""Integration test: only validated agents reach a greedy_pig simulation.

Seven teams join a greedy_pig league and submit through /user/submit-agent-
result (the browser is the executor; the server only gates and persists):
two valid strategies, and five invalid agents that are rejected (recorded as
a SubmissionMetadata attempt with NO linked Submission code row). The test
passes only if exactly the two valid teams reach the simulation payload —
and play against each other when that payload runs through the in-browser
simulation harness.

The five invalid agents fall into two groups, on purpose:

1. Security violations (unauthorized imports, unauthorized `eval`). These
   submit CLAIMED-SUCCESS envelopes — a tampered client asserting the code
   passed — and would *load and play fine in the simulator if they ever
   reached it*: the harness's add_player runs exec() with no AST security
   check. Only the server-side AST gate keeps them out, by refusing the
   Submission code row. Store failed code in Submission and these agents
   leak into the run and show up in total_points.

2. Runtime faults (infinite loop / timeout, divide-by-zero on construction).
   The browser's runner catches these itself — its watchdog kills the
   runaway loop and construction failures surface before the game loop — so
   the browser submits the error envelopes it produced, and the server
   records the attempt without a code row.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.database.db_models import League, Submission, SubmissionMetadata, Team
from backend.tests.conftest import make_student_token
from backend.tests.integration.test_game_workflows import _run_browser_simulation


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


def _submit(client: TestClient, team: Team, code: str, envelope: dict):
    """POST a browser-produced envelope for this team's code."""
    headers = {"Authorization": f"Bearer {make_student_token(team)}"}
    payload = {"code": code, **envelope}
    return client.post(
        "/user/submit-agent-result", headers=headers, json=payload
    )


def _success_envelope(team_name: str) -> dict:
    return {
        "status": "success",
        "feedback": {"game": "greedy_pig"},
        "simulation_results": {
            "total_points": {team_name: 500, "Bot1": 700},
            "num_simulations": 300,
        },
        "duration_ms": 800.0,
    }


# What the browser runner reports for the two runtime-fault agents.
TIMEOUT_ENVELOPE = {
    "status": "error",
    "message": "Your agent consumes too much time - validation did not finish",
    "duration_ms": 20000.0,
}

CONSTRUCTION_ENVELOPE = {
    "status": "error",
    "message": (
        "Failed to create player for team invalid_divide_by_zero: "
        "division by zero"
    ),
    "traceback": "ZeroDivisionError: division by zero",
    "duration_ms": 15.0,
}


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

    # 1. Seven teams submit envelopes. The AST-invalid agents claim success
    #    (a tampered client) and are refused by the server gate; the runtime-
    #    fault agents submit the error envelopes the browser produced. Either
    #    way the attempt is recorded in SubmissionMetadata but no Submission
    #    code row is written.
    claimed_envelopes = {
        "invalid_timeout": TIMEOUT_ENVELOPE,
        "invalid_divide_by_zero": CONSTRUCTION_ENVELOPE,
    }
    teams_by_name = {}
    for name, code in {**valid_teams, **invalid_teams}.items():
        team = _make_team(db_session, greedy_pig_league, name)
        teams_by_name[name] = team
        envelope = claimed_envelopes.get(name, _success_envelope(name))
        response = _submit(client, team, code, envelope)
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

    # 2. Fetch the simulation payload the browser runner would use (as admin —
    #    Admin Institution owns the seeded league). This is the filter under
    #    test: only teams with a stored Submission code row appear.
    submissions_response = client.get(
        f"/user/get-league-submissions/{greedy_pig_league.id}",
        headers=auth_headers,
    )
    assert submissions_response.status_code == 200, submissions_response.text
    submissions = submissions_response.json()
    assert set(submissions.keys()) == set(valid_teams), (
        f"Only validated teams should reach the simulation payload, "
        f"got: {set(submissions.keys())}"
    )

    # 3. The payload plays cleanly through the in-browser harness: only the two
    #    validated teams compete. If failed code ever gets a Submission row
    #    again, the rejected agents (which load and play fine) leak in and the
    #    payload assertion above fails first.
    envelope = _run_browser_simulation("greedy_pig", submissions, 20)
    assert envelope["status"] == "success"
    total_points = envelope["simulation_results"]["total_points"]
    assert set(total_points.keys()) == set(valid_teams)
    for invalid_name in invalid_teams:
        assert invalid_name not in total_points
