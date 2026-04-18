"""
Throwaway seed script: creates 4 greedy_pig teams and submits 4 agents per team
that get progressively better. Strategies are adapted from the validation players.

Usage (API must be up — `docker compose up -d`):
    python seed_greedy_pig_teams.py

No extra deps beyond `requests` (install with `pip install requests` if needed).
"""

import sys
import time

import requests

API = "http://localhost:8000"
INSTITUTION_NAME = "Admin Institution"
INSTITUTION_PASSWORD = "institution"
LEAGUE_NAME = "greedy_pig_league"

TEAM_PASSWORD = "password123"
TEAMS = ["seed_alpha", "seed_bravo", "seed_charlie", "seed_delta"]


# ---------------------------------------------------------------------------
# 4 progressively-improving submissions per team.
# Submission 1 is a naive validation-player-style strategy.
# Submission 4 is a rank/end-game aware strategy.
# ---------------------------------------------------------------------------
SUBMISSIONS = {
    "seed_alpha": [
        # 1. Bank5 clone — banks far too early.
        """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 5:
            return "bank"
        return "continue"
""",
        # 2. Bank15 clone — a clear improvement.
        """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 15:
            return "bank"
        return "continue"
""",
        # 3. StopAt21 clone — pushes harder per turn.
        """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 21:
            return "bank"
        return "continue"
""",
        # 4. End-game aware: bank more cautiously when close to 100.
        """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        unbanked = game_state["unbanked_money"][self.name]
        banked = game_state["banked_money"][self.name]
        if banked + unbanked >= 100:
            return "bank"
        if unbanked > 20:
            return "bank"
        return "continue"
""",
    ],
    "seed_bravo": [
        # 1. BankRoll3 clone — banks after 3 rolls regardless of total.
        """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["roll_no"] == 3:
            return "bank"
        return "continue"
""",
        # 2. BankRoll4 clone — one more roll per turn.
        """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["roll_no"] == 4:
            return "bank"
        return "continue"
""",
        # 3. Hybrid — roll count OR score threshold.
        """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        unbanked = game_state["unbanked_money"][self.name]
        if game_state["roll_no"] >= 4 or unbanked > 18:
            return "bank"
        return "continue"
""",
        # 4. Rank-aware: push harder when trailing, safer when leading.
        """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        unbanked = game_state["unbanked_money"][self.name]
        banked = game_state["banked_money"][self.name]
        rank = self.my_rank(game_state)
        if banked + unbanked >= 100:
            return "bank"
        threshold = 16 if rank == 1 else 24
        if unbanked > threshold:
            return "bank"
        return "continue"
""",
    ],
    "seed_charlie": [
        # 1. Bank at 10 — very conservative.
        """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 10:
            return "bank"
        return "continue"
""",
        # 2. Bank at 17 — more aggressive.
        """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 17:
            return "bank"
        return "continue"
""",
        # 3. Threshold + end-game hook.
        """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        unbanked = game_state["unbanked_money"][self.name]
        banked = game_state["banked_money"][self.name]
        if banked + unbanked >= 100:
            return "bank"
        if unbanked > 20:
            return "bank"
        return "continue"
""",
        # 4. Full adaptive: end-game + rank-aware threshold.
        """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        unbanked = game_state["unbanked_money"][self.name]
        banked = game_state["banked_money"][self.name]
        rank = self.my_rank(game_state)
        if banked + unbanked >= 100:
            return "bank"
        leader_banked = max(game_state["banked_money"].values())
        deficit = leader_banked - banked
        threshold = 18
        if rank == 1:
            threshold = 15
        elif deficit > 20:
            threshold = 26
        if unbanked > threshold:
            return "bank"
        return "continue"
""",
    ],
    "seed_delta": [
        # 1. Random — baseline noise.
        """
from games.greedy_pig.player import Player
import random

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return random.choice(["bank", "continue"])
""",
        # 2. Simple threshold 12.
        """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 12:
            return "bank"
        return "continue"
""",
        # 3. Threshold 18 with end-game.
        """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        unbanked = game_state["unbanked_money"][self.name]
        banked = game_state["banked_money"][self.name]
        if banked + unbanked >= 100:
            return "bank"
        if unbanked > 18:
            return "bank"
        return "continue"
""",
        # 4. Full adaptive, slightly different tuning from charlie #4.
        """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        unbanked = game_state["unbanked_money"][self.name]
        banked = game_state["banked_money"][self.name]
        rank = self.my_rank(game_state)
        if banked + unbanked >= 100:
            return "bank"
        leader_banked = max(game_state["banked_money"].values())
        deficit = leader_banked - banked
        if rank == 1:
            threshold = 17
        elif deficit > 25:
            threshold = 28
        else:
            threshold = 20
        if game_state["roll_no"] >= 6:
            threshold = min(threshold, 15)
        if unbanked > threshold:
            return "bank"
        return "continue"
""",
    ],
}


def post(path, token=None, json_body=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.post(f"{API}{path}", headers=headers, json=json_body or {}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("status") == "error":
        raise RuntimeError(f"{path} -> {data.get('message')}")
    return data


def institution_login():
    data = post(
        "/auth/institution-login",
        json_body={"name": INSTITUTION_NAME, "password": INSTITUTION_PASSWORD},
    )
    return data["data"]["access_token"]


def team_login(name):
    data = post(
        "/auth/team-login",
        json_body={"name": name, "password": TEAM_PASSWORD},
    )
    return data["data"]["access_token"]


def create_team(inst_token, name):
    try:
        post(
            "/institution/team-create",
            token=inst_token,
            json_body={
                "name": name,
                "password": TEAM_PASSWORD,
                "school_name": "Seed School",
            },
        )
        print(f"  created team {name}")
    except RuntimeError as e:
        # already exists is fine for a throwaway re-run
        if "already" in str(e).lower() or "exists" in str(e).lower():
            print(f"  team {name} already exists — reusing")
        else:
            raise


def assign_league(team_token, league_name):
    post(
        "/user/league-assign",
        token=team_token,
        json_body={"name": league_name},
    )


def submit(team_token, code):
    return post(
        "/user/submit-agent",
        token=team_token,
        json_body={"code": code},
    )


def main():
    print(f"logging in as institution '{INSTITUTION_NAME}'...")
    inst_token = institution_login()

    print("creating teams...")
    for name in TEAMS:
        create_team(inst_token, name)

    for name in TEAMS:
        print(f"\n=== {name} ===")
        token = team_login(name)
        assign_league(token, LEAGUE_NAME)
        print(f"  assigned to league '{LEAGUE_NAME}'")
        for i, code in enumerate(SUBMISSIONS[name], start=1):
            resp = submit(token, code)
            print(f"  submission {i}/4 OK — {resp.get('message', '')[:80]}")
            # stay under the 5-submissions-per-minute cap
            time.sleep(13)

    print("\nall done.")


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"HTTP error: {e.response.status_code} {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
