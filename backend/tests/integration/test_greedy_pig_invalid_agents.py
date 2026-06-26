"""Integration test: invalid agents are filtered out before a greedy_pig simulation.

Five teams join a greedy_pig league. Three submit code that fails validation
(an infinite loop / timeout, a divide-by-zero, and a runaway recursion "memory
bomb"); two submit valid strategies. The submit-agent endpoint runs every
submission through the real validator service, so the three bad agents are
stored with passed_validation=False and are skipped when the simulator fetches
the league's submissions. The test passes only if exactly the two valid teams
make it into the simulation and play against each other.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from backend.database.db_models import League, Team
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

# Times out: a busy loop that never returns. The validator kills the runaway
# child after its hard timeout, so validation fails.
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

# Memory bomb via unbounded recursion on construction -> RecursionError before
# the game ever runs, so validation fails.
INVALID_MEMORY_BOMB = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def __init__(self):
        super().__init__()
        self._explode()

    def _explode(self):
        return self._explode()

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


def test_only_valid_agents_reach_greedy_pig_simulation(
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
        "invalid_timeout": INVALID_TIMEOUT,
        "invalid_divide_by_zero": INVALID_DIVIDE_BY_ZERO,
        "invalid_memory_bomb": INVALID_MEMORY_BOMB,
    }

    # 1. Five teams submit code through the real validator.
    for name, code in {**valid_teams, **invalid_teams}.items():
        team = _make_team(db_session, greedy_pig_league, name)
        response = _submit(client, team, code)
        assert response.status_code == 200
        status = response.json()["status"]
        if name in valid_teams:
            assert status == "success", f"{name} should pass validation: {response.json()}"
        else:
            assert status == "error", f"{name} should fail validation: {response.json()}"

    # 2. Run the simulation as admin (Admin Institution owns the seeded league).
    sim_response = client.post(
        "/institution/run-simulation",
        headers=auth_headers,
        json={"league_id": greedy_pig_league.id, "num_simulations": 20},
    )
    assert sim_response.status_code == 200, sim_response.text
    sim_data = sim_response.json()
    assert sim_data["status"] == "success", sim_data

    # 3. Only the two valid teams should have played.
    total_points = sim_data["data"]["total_points"]
    assert set(total_points.keys()) == set(valid_teams), (
        f"Only valid teams should reach the simulation, got: {set(total_points.keys())}"
    )
    for invalid_name in invalid_teams:
        assert invalid_name not in total_points
