import itertools
import random

from backend.games.base_game import BaseGame

GRID_SIZE = 100
MOVE_CAP = 1000
ATTACKER_BOOSTS = 5
DEFENDER_BOOSTS = 10
DEFENDER_START_X = 70
MINES_PER_PLAYER = 1

DIRECTIONS = {
    "N": (0, 1),
    "S": (0, -1),
    "E": (1, 0),
    "W": (-1, 0),
    "STAY": (0, 0),
}

# [survival_max, catch_bonus, breakthrough_base, speed_bonus_max, progress_max]
DEFAULT_REWARDS = [100, 100, 100, 100, 50]


class BreakthroughGame(BaseGame):
    starter_code = """
from games.breakthrough.player import Player
import random

class CustomPlayer(Player):
    def make_decision(self, game_state):
        # game_state keys:
        #   turn        - current turn number (1..move_cap)
        #   role        - "attacker" or "defender" (you play BOTH across matches)
        #   my_pos      - your (x, y); x=0 is the left edge, x=99 the right edge (goal)
        #   opp_pos     - opponent's (x, y)
        #   my_boosts   - boosts you have left (attacker starts with 5, defender 10)
        #   opp_boosts  - opponent's remaining boosts
        #   my_mines    - mines you have left to lay (everyone starts with 1)
        #   opp_mines   - opponent's mines left to lay
        #   my_mine     - where your laid mine sits, or None
        #   opp_frozen  - True if the opponent hit a mine (they can't move again)
        #   my_trace    - list of every cell you have visited
        #   opp_trace   - list of every cell your opponent has visited
        #   grid_size   - 100
        #   move_cap    - 1000
        #
        # Return "N" / "S" / "E" / "W" / "STAY",
        # or {"direction": "E", "boost": True} to jump 2 cells (uses a boost),
        # or {"direction": "N", "mine": True} to lay a mine on the cell you are
        # leaving. An opponent who ends a move on your mine is blown up and
        # can't move for the rest of the match (your own mine never hurts you).

        my_x, my_y = game_state["my_pos"]
        opp_x, opp_y = game_state["opp_pos"]

        if game_state["role"] == "attacker":
            # Sprint for the right edge; deal with the defender if they block us
            if opp_y == my_y and 0 < opp_x - my_x <= 2:
                if game_state["my_boosts"] > 0 and opp_x - my_x == 1:
                    return {"direction": "E", "boost": True}  # jump over them!
                return "N" if my_y < game_state["grid_size"] - 1 else "S"
            return "E"

        # Defender: chase the attacker, closing the bigger gap first
        dx = opp_x - my_x
        dy = opp_y - my_y
        if abs(dx) >= abs(dy) and dx != 0:
            return "E" if dx > 0 else "W"
        if dy != 0:
            return "N" if dy > 0 else "S"
        return "STAY"
"""

    game_instructions = """
# Breakthrough Game Instructions

## 1. Game Objective

A 1v1 pursuit duel on a 100x100 grid. One dot attacks, one defends.
**Both players pick their moves at the same time** — neither knows what the
other is about to do.

- **Attacker** starts on the left edge and wins by reaching any cell in the
  rightmost column (x = 99). Has **5 boosts**.
- **Defender** starts at column 70 and wins by catching the attacker or by
  holding out until the move cap (1000 turns). Has **10 boosts**.
- **Both** carry **one mine**.

## 2. Your Task

Implement `make_decision(game_state)` for **both roles** — every pairing plays
twice, once in each role, and your points from both matches are added together
(check `game_state["role"]`).

Each turn, return a move:
- One cell in a direction: `"N"`, `"S"`, `"E"`, `"W"`, or `"STAY"`.
- **Boost**: `{"direction": "E", "boost": True}` jumps **2 cells**, leaping
  over the middle cell — including over the other player!
- **Mine**: `{"direction": "N", "mine": True}` lays your mine on the cell you
  are standing on *before* you move. You only have one per match.
- Invalid moves (off the grid, boosting with none left, errors in your code)
  count as `"STAY"`.

**Getting caught** — after both moves resolve, the attacker is caught if both
players end on the **same cell**, or the players **swap cells** (moved through
each other). A boost-jump *over* an opponent is safe — but landing on the cell
they end their move on is a catch.

**Mines** — an opponent who **ends a move** on your mine is blown up: they
never move again for the rest of the match. Your own mine never hurts you, and
a boost-jump *over* a mine is safe. Mines are invisible — but they can only be
laid on a cell the owner was standing on, so the opponent's trace is the map of
every possible mine. A blown-up defender cannot catch anyone (stepping onto a
mine beats a same-cell or swap catch on the same turn); a blown-up attacker is
a sitting duck — walk over and catch them.

## 3. Available Information

`game_state` contains:
- `turn` — current turn number (1..move_cap)
- `role` — `"attacker"` or `"defender"`
- `my_pos` / `opp_pos` — (x, y) positions; x=0 is the left edge, x=99 the goal
- `my_boosts` / `opp_boosts` — boosts remaining
- `my_mines` / `opp_mines` — mines left to lay (everyone starts with 1)
- `my_mine` — where your laid mine sits, or `None` (the opponent's is hidden)
- `opp_frozen` — `True` once the opponent has been blown up by your mine
- `my_trace` / `opp_trace` — every cell each dot has visited, in order
- `grid_size` (100) and `move_cap` (1000)

## 4. Scoring (defaults)

- **Defender**: survival points grow with every turn the attacker is kept at
  bay (up to 100 at the move cap), plus a **+100 catch bonus**. A catch is
  always worth more than a mere timeout.
- **Attacker**: breaking through earns 100 plus a speed bonus of up to 100
  (faster = more). If caught or timed out, partial credit of up to 50 for how
  far right you got.

## 5. Strategy Tips

- Moves are simultaneous: predict where the opponent **will be**, not where
  they are. Feint before you commit.
- The opponent's trace reveals their habits — do they always dodge north?
- As defender, staying between the attacker and the right edge beats chasing
  from behind; save boosts to recover when they jump over you.
- As attacker, a boost wasted in open field is a boost you won't have at the
  wall.
- A mine laid on your own cell just before you dodge turns a chasing defender's
  swap-catch into their funeral. Save it for the moment you're about to be
  caught.
- Once the opponent's mine count hits 0, every cell in their trace could be the
  mine. If you never end a move on their old cells, you can never be blown up.
- Add feedback with `self.add_feedback()` to debug your strategy in the replay.
"""

    reward_schema = {
        "kind": "matrix",
        "length": 5,
        "labels": [
            "Defender survival max",
            "Defender catch bonus",
            "Attacker breakthrough base",
            "Attacker speed bonus max",
            "Attacker progress max",
        ],
        "default": list(DEFAULT_REWARDS),
    }

    reward_instructions = """## Custom Rewards — Breakthrough

Five numbers tune the scoring:

1. **Defender survival max** — defender earns `survival_max * turns / 1000`
   (the full amount on a timeout)
2. **Defender catch bonus** — added on top of survival when the defender
   catches the attacker
3. **Attacker breakthrough base** — flat points for reaching the right edge
4. **Attacker speed bonus max** — extra `speed_max * (1000 - turns) / 1000`
   for breaking through quickly
5. **Attacker progress max** — consolation `progress_max * furthest_x / 99`
   when caught or timed out

Defaults: `[100, 100, 100, 100, 50]`.
"""

    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)
        self.grid_size = GRID_SIZE
        self.move_cap = MOVE_CAP
        self.attacker_boosts = ATTACKER_BOOSTS
        self.defender_boosts = DEFENDER_BOOSTS
        self.defender_start_x = DEFENDER_START_X
        self.mines_per_player = MINES_PER_PLAYER
        self.game_feedback = {"game": "breakthrough", "matches": []}

    def _validate_rewards(self, custom_rewards):
        if (
            isinstance(custom_rewards, (list, tuple))
            and len(custom_rewards) == len(DEFAULT_REWARDS)
            and all(isinstance(v, (int, float)) and v >= 0 for v in custom_rewards)
        ):
            return [float(v) for v in custom_rewards]
        return [float(v) for v in DEFAULT_REWARDS]

    def _normalize_move(self, raw):
        """Return (direction, boost, mine) or None if the move is invalid."""
        if isinstance(raw, str):
            direction, boost, mine = raw, False, False
        elif isinstance(raw, dict):
            direction = raw.get("direction")
            boost = bool(raw.get("boost", False))
            mine = bool(raw.get("mine", False))
        else:
            return None
        if direction not in DIRECTIONS:
            return None
        if direction == "STAY":
            boost = False
        return direction, boost, mine

    def _safe_decision(self, player, game_state):
        """Get a player's move; anything invalid resolves to STAY."""
        try:
            raw = player.make_decision(game_state)
        except Exception as e:
            if self.verbose:
                player.add_feedback(f"Error in make_decision ({e}) — treated as STAY")
            return "STAY", False, False
        move = self._normalize_move(raw)
        if move is None:
            if self.verbose:
                player.add_feedback(f"Invalid move {raw!r} — treated as STAY")
            return "STAY", False, False
        return move

    def _resolve_move(self, pos, direction, boost, boosts_left):
        """Return (new_pos, boost_used). Off-grid or unaffordable boosts → stay put."""
        if boost and boosts_left <= 0:
            return pos, False
        dx, dy = DIRECTIONS[direction]
        step = 2 if boost else 1
        nx, ny = pos[0] + dx * step, pos[1] + dy * step
        if not (0 <= nx < self.grid_size and 0 <= ny < self.grid_size):
            return pos, False
        return (nx, ny), boost

    def _build_state(
        self, role, turn, my_pos, opp_pos, my_boosts, opp_boosts, my_trace, opp_trace,
        my_mines, opp_mines, my_mine, opp_frozen,
    ):
        return {
            "turn": turn,
            "role": role,
            "my_pos": my_pos,
            "opp_pos": opp_pos,
            "my_boosts": my_boosts,
            "opp_boosts": opp_boosts,
            "my_mines": my_mines,
            "opp_mines": opp_mines,
            "my_mine": my_mine,
            "opp_frozen": opp_frozen,
            "my_trace": list(my_trace),
            "opp_trace": list(opp_trace),
            "grid_size": self.grid_size,
            "move_cap": self.move_cap,
        }

    def _score(self, result, turn, furthest_x, rewards):
        """Return (attacker_score, defender_score) for a finished match."""
        survival_max, catch_bonus, breakthrough_base, speed_bonus_max, progress_max = rewards
        goal_x = self.grid_size - 1
        survival = survival_max * turn / self.move_cap
        progress = progress_max * furthest_x / goal_x
        if result == "caught":
            return progress, survival + catch_bonus
        if result == "breakthrough":
            return breakthrough_base + speed_bonus_max * (self.move_cap - turn) / self.move_cap, survival
        return progress, survival_max  # timeout

    def _collect_feedback(self, player):
        if player.feedback:
            name = str(player.name)
            self.player_feedback.setdefault(name, []).extend(player.feedback)
        player.feedback = []

    def play_match(self, attacker, defender, rewards, start_positions=None):
        """Play one match. Returns (match_feedback, attacker_score, defender_score)."""
        if start_positions:
            a_pos = tuple(start_positions[0])
            d_pos = tuple(start_positions[1])
        else:
            margin = min(20, self.grid_size // 5)
            start_x = min(self.defender_start_x, self.grid_size - 2)
            a_pos = (0, random.randint(margin, self.grid_size - 1 - margin))
            d_pos = (start_x, random.randint(margin, self.grid_size - 1 - margin))

        attacker.role = "attacker"
        defender.role = "defender"
        a_boosts, d_boosts = self.attacker_boosts, self.defender_boosts
        a_mines = d_mines = self.mines_per_player
        a_mine_pos = d_mine_pos = None  # where each player's own mine sits
        a_frozen = d_frozen = False
        a_trace, d_trace = [a_pos], [d_pos]
        furthest_x = a_pos[0]
        goal_x = self.grid_size - 1

        match = {
            "attacker": str(attacker.name),
            "defender": str(defender.name),
            "start": {"a": list(a_pos), "d": list(d_pos)},
            "boosts": {"attacker": a_boosts, "defender": d_boosts},
            "mines": {"attacker": a_mines, "defender": d_mines},
            "grid_size": self.grid_size,
            "turns": [],
            "result": None,
            "end_turn": 0,
        }

        result = None
        turn = 0
        while turn < self.move_cap:
            turn += 1
            if a_frozen:
                a_dir, a_boost, a_mine = "STAY", False, False
            else:
                a_state = self._build_state(
                    "attacker", turn, a_pos, d_pos, a_boosts, d_boosts, a_trace, d_trace,
                    a_mines, d_mines, a_mine_pos, d_frozen,
                )
                a_dir, a_boost, a_mine = self._safe_decision(attacker, a_state)
            if d_frozen:
                d_dir, d_boost, d_mine = "STAY", False, False
            else:
                d_state = self._build_state(
                    "defender", turn, d_pos, a_pos, d_boosts, a_boosts, d_trace, a_trace,
                    d_mines, a_mines, d_mine_pos, a_frozen,
                )
                d_dir, d_boost, d_mine = self._safe_decision(defender, d_state)

            # Mines are laid on the cell the player stands on, before moving
            a_laid = d_laid = None
            if a_mine and a_mines > 0:
                a_mines -= 1
                a_mine_pos = a_pos
                a_laid = a_pos
            if d_mine and d_mines > 0:
                d_mines -= 1
                d_mine_pos = d_pos
                d_laid = d_pos

            new_a, a_used = self._resolve_move(a_pos, a_dir, a_boost, a_boosts)
            new_d, d_used = self._resolve_move(d_pos, d_dir, d_boost, d_boosts)
            if a_used:
                a_boosts -= 1
            if d_used:
                d_boosts -= 1

            # Ending a move on the opponent's mine blows you up (owner is immune)
            a_hit = d_mine_pos is not None and new_a == d_mine_pos
            d_hit = a_mine_pos is not None and new_d == a_mine_pos
            if a_hit:
                a_frozen = True
                d_mine_pos = None
            if d_hit:
                d_frozen = True
                a_mine_pos = None

            # Same cell, or moved through each other; a blown-up defender can't catch
            caught = not d_frozen and (
                new_a == new_d or (new_a == d_pos and new_d == a_pos)
            )

            a_pos, d_pos = new_a, new_d
            if a_trace[-1] != a_pos:
                a_trace.append(a_pos)
            if d_trace[-1] != d_pos:
                d_trace.append(d_pos)
            furthest_x = max(furthest_x, a_pos[0])

            if self.verbose:
                turn_record = {
                    "a": list(a_pos),
                    "d": list(d_pos),
                    "ab": int(a_used),
                    "db": int(d_used),
                }
                if a_laid:
                    turn_record["am"] = list(a_laid)
                if d_laid:
                    turn_record["dm"] = list(d_laid)
                if a_hit:
                    turn_record["ax"] = 1
                if d_hit:
                    turn_record["dx"] = 1
                if attacker.feedback:
                    turn_record["af"] = list(attacker.feedback)
                if defender.feedback:
                    turn_record["df"] = list(defender.feedback)
                match["turns"].append(turn_record)
                self._collect_feedback(attacker)
                self._collect_feedback(defender)
            else:
                attacker.feedback = []
                defender.feedback = []

            if caught:
                result = "caught"
                break
            if not a_frozen and a_pos[0] >= goal_x:
                result = "breakthrough"
                break
            if a_frozen and d_frozen:
                # Nobody can ever move again — play out as a timeout
                turn = self.move_cap
                break

        if result is None:
            result = "timeout"

        a_score, d_score = self._score(result, turn, furthest_x, rewards)
        match["result"] = result
        match["end_turn"] = turn
        match["final"] = {"a": list(a_pos), "d": list(d_pos)}
        match["scores"] = {
            str(attacker.name): round(a_score, 1),
            str(defender.name): round(d_score, 1),
        }
        return match, a_score, d_score

    def play_game(self, custom_rewards=None):
        """Round-robin: every pair plays twice, once in each role."""
        self.game_feedback = {"game": "breakthrough", "matches": []}
        self.player_feedback = {}
        rewards = self._validate_rewards(custom_rewards)

        scores = {str(p.name): 0.0 for p in self.players}
        wins = {str(p.name): 0 for p in self.players}
        catches = {str(p.name): 0 for p in self.players}
        breakthroughs = {str(p.name): 0 for p in self.players}
        matches_played = {str(p.name): 0 for p in self.players}

        player_pairs = list(itertools.combinations(self.players, 2))
        random.shuffle(player_pairs)

        for p1, p2 in player_pairs:
            for attacker, defender in ((p1, p2), (p2, p1)):
                match, a_score, d_score = self.play_match(attacker, defender, rewards)
                a_name, d_name = str(attacker.name), str(defender.name)

                matches_played[a_name] += 1
                matches_played[d_name] += 1
                scores[a_name] += a_score
                scores[d_name] += d_score

                if match["result"] == "breakthrough":
                    wins[a_name] += 1
                    breakthroughs[a_name] += 1
                else:
                    wins[d_name] += 1
                    if match["result"] == "caught":
                        catches[d_name] += 1

                if self.verbose:
                    self.game_feedback["matches"].append(match)

        points = {name: round(value, 1) for name, value in scores.items()}
        return {
            "points": points,
            "score_aggregate": dict(points),
            "table": {
                "matches_played": matches_played,
                "wins": wins,
                "catches": catches,
                "breakthroughs": breakthroughs,
            },
        }

    def run_simulations(self, num_simulations, league, custom_rewards=None):
        """Run multiple simulations, capping total matches (matches run up to 1000 turns)."""
        num_players = len(self.players)
        matches_per_sim = num_players * (num_players - 1)
        if matches_per_sim and matches_per_sim * num_simulations > 1000:
            num_simulations = max(1, 1000 // matches_per_sim)

        total_points = {str(p.name): 0.0 for p in self.players}
        total_wins = {str(p.name): 0 for p in self.players}
        total_catches = {str(p.name): 0 for p in self.players}
        total_breakthroughs = {str(p.name): 0 for p in self.players}
        total_games_played = {str(p.name): 0 for p in self.players}

        for _ in range(num_simulations):
            self.reset()
            results = self.play_game(custom_rewards)

            for name, points in results["points"].items():
                total_points[str(name)] += points
            for name, value in results["table"]["wins"].items():
                total_wins[str(name)] += value
            for name, value in results["table"]["catches"].items():
                total_catches[str(name)] += value
            for name, value in results["table"]["breakthroughs"].items():
                total_breakthroughs[str(name)] += value
            for name, value in results["table"]["matches_played"].items():
                total_games_played[str(name)] += value

        actual_games_played = sum(total_games_played.values()) // 2

        return {
            "total_points": {name: round(value, 1) for name, value in total_points.items()},
            "num_simulations": actual_games_played,
            "table": {
                "wins": total_wins,
                "games_played": total_games_played,
                "catches": total_catches,
                "breakthroughs": total_breakthroughs,
            },
        }

    def reset(self):
        super().reset()
        self.game_feedback = {"game": "breakthrough", "matches": []}
