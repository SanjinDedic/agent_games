"""
Seed the production deployment with a test institution, teams, league, and submissions.
Run: python seed_prod.py
"""

import requests
import sys
import time

API = "https://api.agentgames.io"
ADMIN_USER = "admin"
ADMIN_PASS = "2rg5OxrZrtu5"

INST_NAME = "TestAcd"
INST_PASS = "inst99"
INST_EMAIL = "demo@test.com"

TEAMS = [
    {"name": "Foxes", "password": "fox111"},
    {"name": "Hawks", "password": "hwk222"},
    {"name": "Lions", "password": "lio333"},
    {"name": "Wolves", "password": "wlf444"},
]

LEAGUE_NAME = "lineup4_amazing_demo"
GAME = "lineup4"


def api(method, path, token=None, **kwargs):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = getattr(requests, method)(f"{API}{path}", headers=headers, **kwargs)
    r.raise_for_status()
    data = r.json()
    if data.get("status") == "error":
        print(f"  ERROR {path}: {data.get('message')}")
        sys.exit(1)
    return data


def main():
    # 1. Admin login
    print("Logging in as admin...")
    resp = api("post", "/auth/admin-login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
    admin_token = resp["data"]["access_token"]

    # 2. Create institution
    print(f"Creating institution '{INST_NAME}'...")
    resp = api("post", "/admin/institution-create", token=admin_token, json={
        "name": INST_NAME,
        "contact_person": "Test",
        "contact_email": INST_EMAIL,
        "password": INST_PASS,
        "subscription_expiry": "2027-01-01T00:00:00",
        "docker_access": True,
    })
    print(f"  Institution created: {resp['data']}")

    # 3. Institution login
    print("Logging in as institution...")
    resp = api("post", "/auth/institution-login", json={"name": INST_NAME, "password": INST_PASS})
    inst_token = resp["data"]["access_token"]

    # 4. Create league
    print(f"Creating league '{LEAGUE_NAME}'...")
    resp = api("post", "/institution/league-create", token=inst_token, json={
        "name": LEAGUE_NAME,
        "game": GAME,
    })
    league_id = resp["data"]["league_id"]
    print(f"  League ID: {league_id}")

    # 5. Create teams
    team_ids = []
    for t in TEAMS:
        print(f"Creating team '{t['name']}'...")
        resp = api("post", "/institution/team-create", token=inst_token, json={
            "name": t["name"],
            "password": t["password"],
        })
        team_ids.append(resp["data"]["team_id"])
        print(f"  Team ID: {resp['data']['team_id']}")

    # 6. Assign teams to league
    for tid in team_ids:
        print(f"Assigning team {tid} to league {league_id}...")
        api("post", "/institution/assign-team-to-league", token=inst_token, json={
            "team_id": tid,
            "league_id": league_id,
        })

    # 7. Submit code for each team (3 submissions each with slight variations)
    agent_templates = [
        # Version 1: random player
        '''import random
from games.lineup4.player import Player

class CustomPlayer(Player):
    PREFERRED = [{cols}]
    def make_decision(self, game_state):
        for col in self.PREFERRED:
            for move in game_state["possible_moves"]:
                if int(move[0]) == col:
                    return move
        return random.choice(game_state["possible_moves"])
''',
        # Version 2: adds blocking
        '''import random
from games.lineup4.player import Player

class CustomPlayer(Player):
    PREFERRED = [{cols}]
    def make_decision(self, game_state):
        board = game_state["board"]
        moves = game_state["possible_moves"]
        opp = "O" if self.symbol == "X" else "X"
        for m in moves:
            board[m] = opp
            if self._wins(board, opp, m):
                board[m] = None
                return m
            board[m] = None
        for col in self.PREFERRED:
            for m in moves:
                if int(m[0]) == col:
                    return m
        return random.choice(moves)

    def _wins(self, board, sym, pos):
        for ws in self.all_winning_sets:
            if pos in ws and all(board[p] == sym for p in ws):
                return True
        return False
''',
        # Version 3: win check + block
        '''import random
from games.lineup4.player import Player

class CustomPlayer(Player):
    PREFERRED = [{cols}]
    def make_decision(self, game_state):
        board = game_state["board"]
        moves = game_state["possible_moves"]
        opp = "O" if self.symbol == "X" else "X"
        for m in moves:
            board[m] = self.symbol
            if self._wins(board, self.symbol, m):
                board[m] = None
                return m
            board[m] = None
        for m in moves:
            board[m] = opp
            if self._wins(board, opp, m):
                board[m] = None
                return m
            board[m] = None
        for col in self.PREFERRED:
            for m in moves:
                if int(m[0]) == col:
                    return m
        return random.choice(moves)

    def _wins(self, board, sym, pos):
        for ws in self.all_winning_sets:
            if pos in ws and all(board[p] == sym for p in ws):
                return True
        return False
''',
    ]

    # Different column preferences per team
    col_prefs = [
        "4, 3, 5, 2, 6, 1, 7",
        "3, 4, 5, 2, 6, 1, 7",
        "5, 4, 3, 6, 2, 7, 1",
        "4, 5, 3, 6, 2, 1, 7",
    ]

    for i, t in enumerate(TEAMS):
        print(f"Logging in as team '{t['name']}'...")
        resp = api("post", "/auth/team-login", json={"name": t["name"], "password": t["password"]})
        team_token = resp["data"]["access_token"]

        for v, template in enumerate(agent_templates):
            code = template.format(cols=col_prefs[i])
            print(f"  Submitting v{v+1} for {t['name']}...")
            resp = api("post", "/user/submit-agent", token=team_token, json={"code": code})
            print(f"    {resp['message']}")
            time.sleep(1)  # avoid rate limit

    # Print credentials
    print("\n" + "=" * 50)
    print("CREDENTIALS")
    print("=" * 50)
    print(f"\nInstitution: {INST_NAME} / {INST_PASS}")
    print(f"League: {LEAGUE_NAME} (ID: {league_id})")
    print(f"\nTeams:")
    for t in TEAMS:
        print(f"  {t['name']:10s} / {t['password']}")
    print()


if __name__ == "__main__":
    main()
