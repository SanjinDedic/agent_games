"""Hearts — the classic trick-avoidance card game, played at tables of 4.

Tournament structure (driven by the simulation task calling play_game
num_simulations times on one instance; None results are skipped):

- 4 to EXHAUSTIVE_MAX_PLAYERS players: every possible group of 4 plays one
  game per play_game call (one exhaustive pass), until MAX_TOTAL_GAMES.
- More players: semi-random tables of 4 (greedy pair-coverage scheduler,
  byes rotate to the most-played players) until every player has played
  RECENT_GAMES_WINDOW games or MAX_TOTAL_GAMES is hit. Rankings count each
  player's most recent RECENT_GAMES_WINDOW games only — play_game reports
  per-call deltas of that sliding-window total, so the aggregator's running
  sum always equals the windowed total.

Scoring: placement points per game (default 4/2/1/0, ties share the mean).
The raw Hearts score only feeds placements and the avg_points_per_hand stat.
"""

import copy
import itertools
import random
from collections import deque

from backend.games.base_game import BaseGame

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
RANK_VALUE = {r: i for i, r in enumerate(RANKS, start=2)}
SUITS = ["C", "D", "S", "H"]
DECK = [r + s for s in SUITS for r in RANKS]

TABLE_SIZE = 4
PASS_DIRECTIONS = ["left", "right", "across", "hold"]
DEFAULT_REWARDS = [4, 2, 1, 0]  # placement points for 1st..4th (lowest score first)


def card_suit(card):
    return card[-1]


def card_rank_value(card):
    return RANK_VALUE[card[:-1]]


def card_points(card):
    if card_suit(card) == "H":
        return 1
    if card == "QS":
        return 13
    return 0


def sort_hand(cards):
    return sorted(cards, key=lambda c: (SUITS.index(card_suit(c)), card_rank_value(c)))


class TableScheduler:
    """Semi-random tables of 4: greedy pair coverage, byes to the most-played.

    Round-based version of docs/hearts_tournament_scheduler.py phase 1. When
    every pair has met, the uncovered set refills so later rounds keep mixing
    opponents instead of collapsing into repeats.
    """

    def __init__(self, names, rng):
        self.names = list(names)
        self.rng = rng
        self.count = {p: 0 for p in self.names}
        self.uncovered = set(itertools.combinations(sorted(self.names), 2))

    def _pair(self, p, q):
        return (p, q) if p < q else (q, p)

    def _new_pairs(self, table, q):
        return sum(1 for p in table if self._pair(p, q) in self.uncovered)

    def _uncovered_degree(self, p, pool):
        return sum(1 for q in pool if q != p and self._pair(p, q) in self.uncovered)

    def next_round(self):
        """One round of player-disjoint tables covering all but n % 4 players."""
        if not self.uncovered:
            self.uncovered = set(itertools.combinations(sorted(self.names), 2))
        n_byes = len(self.names) % TABLE_SIZE
        order = sorted(self.names, key=lambda p: (self.count[p], self.rng.random()))
        pool = set(order[: len(self.names) - n_byes])
        tables = []
        while pool:
            seed_p = max(
                pool, key=lambda p: (self._uncovered_degree(p, pool), self.rng.random())
            )
            table = [seed_p]
            pool.remove(seed_p)
            for _ in range(TABLE_SIZE - 1):
                nxt = max(
                    pool,
                    key=lambda q: (
                        self._new_pairs(table, q),
                        -self.count[q],
                        self.rng.random(),
                    ),
                )
                table.append(nxt)
                pool.remove(nxt)
            for p, q in itertools.combinations(table, 2):
                self.uncovered.discard(self._pair(p, q))
            for p in table:
                self.count[p] += 1
            tables.append(tuple(table))
        return tables


class HeartsGame(BaseGame):
    TARGET_SCORE = 100
    MAX_HANDS = 25  # someone must reach 100 within 16 hands; hard backstop
    EXHAUSTIVE_MAX_PLAYERS = 20
    RECENT_GAMES_WINDOW = 500
    SCHEDULER_ROUNDS_PER_CALL = 5
    MAX_TOTAL_GAMES = 6000

    # Benchmarked: one pass plays every table of 4 exhaustively (~374ms with
    # the 8 validation bots + submission), so 2 passes keep validation <1s.
    validation_simulations = 2

    starter_code = """
from games.hearts.player import Player
import random

class CustomPlayer(Player):
    def make_decision(self, game_state):
        # Card codes are rank + suit letter: "QS", "10H", "2C", "AD"

        # ---- available in BOTH phases -----------------------------------
        phase = game_state["phase"]          # "pass" or "play"
        hand = game_state["hand"]            # your current cards (list of codes)
        scores = game_state["scores"]        # running game score per player {name: points}
        players = game_state["players"]      # seat order, list of player names

        if phase == "pass":
            # ---- available only in the PASS phase -----------------------
            pass_direction = game_state["pass_direction"]  # "left"/"right"/"across"/"hold"
            hand_number = game_state["hand_number"]        # which hand of the game (1, 2, 3, ...)

            self.add_feedback(f"Hand {hand_number}: passing {pass_direction}, hand is {hand}")

            # Choose exactly 3 cards from your hand to pass on.
            return random.sample(hand, 3)

        # ---- available only in the PLAY phase ---------------------------
        legal_moves = game_state["legal_moves"]          # cards you may play right now
        trick = game_state["trick"]                      # this trick so far: [{"player", "card"}, ...]
        trick_number = game_state["trick_number"]        # 1..13
        leader = game_state["leader"]                    # name of who led this trick
        hearts_broken = game_state["hearts_broken"]      # have hearts been broken yet? (bool)
        points_taken = game_state["points_taken"]        # points each player took THIS hand {name: pts}
        cards_played = game_state["cards_played"]         # every card played this hand so far (in order)
        cards_remaining = game_state["cards_remaining"]   # every card not yet played (includes your hand)

        # ---- round-based info printed to the game output ----------------
        self.add_feedback(f"Trick {trick_number}: choosing from {legal_moves}")
        self.add_feedback(f"Cards played so far ({len(cards_played)}): {cards_played}")
        self.add_feedback(f"Hearts broken: {hearts_broken} | points this hand: {points_taken}")

        return random.choice(legal_moves)  # fallback to random legal card
"""

    game_instructions = """
# Hearts Game Instructions

The classic trick-avoidance card game, played at tables of 4.

**New to Hearts?** Play a few rounds yourself at
[cardgames.io/hearts](https://cardgames.io/hearts/) — it is the fastest way to
get the rules to click before you start coding your agent.

## Game Objective
Score as few points as possible. Each heart you take is 1 point and the Queen
of Spades is 13. The game ends when someone reaches 100 points — the player
with the **fewest** points wins the table. Exception: take *all* 26 points in
one hand ("shooting the moon") and the other three players get 26 instead.

## What is a trick?
A **trick** is one round where each of the 4 players plays a single card, in
seat order. The first player "leads" a card, setting the **led suit**; the other
three follow in turn. Whoever played the highest card *of the led suit* wins
(takes) the trick, collects all 4 cards, and leads the next trick.

## Game Rules
- Each hand, all 52 cards are dealt (13 each), then each player passes 3 cards
  (direction cycles: left, right, across, hold — no pass on the 4th hand)
- The player holding the 2 of Clubs leads it to the first trick
- You must follow the led suit if you can (play a card of the same suit as the
  card that was led); the highest card of the led suit takes the trick and leads next
- If you can't follow suit, you may play any card — this is how you "dump"
  penalty cards (hearts, Queen of Spades) onto whoever wins the trick
- You can't lead hearts until hearts are "broken" (a heart was discarded), and
  no penalty card (hearts, Queen of Spades) may be played on the first trick unless forced

## Your Task
Implement `make_decision(game_state)`; it is called for both phases:
- `game_state["phase"] == "pass"` → return a list of exactly 3 card codes from `game_state["hand"]`
- `game_state["phase"] == "play"` → return one card code from `game_state["legal_moves"]`

Card codes are rank + suit letter: `"QS"`, `"10H"`, `"2C"`, `"AD"`.

## Available Information
In the `game_state` dictionary:
- `phase`: `"pass"` or `"play"`
- `hand`: your current cards
- `legal_moves`: the cards you may play right now (play phase)
- `trick`: cards played so far this trick, in order — `[{"player", "card"}, ...]`
- `trick_number` (1-13), `leader`, `hearts_broken`
- `points_taken`: points each player has taken this hand
- `cards_played`: every card played this hand so far (all completed tricks plus
  the current trick before your turn), in play order
- `cards_remaining`: every card not yet played this hand (includes your own
  hand). `cards_played` + `cards_remaining` is always the full 52-card deck
- `scores`: running game scores; `players`: seat order; `pass_direction`, `hand_number` (pass phase)

## Strategy Tips
1. Pass your high spades (Q/K/A) and high hearts — or keep them if you plan to shoot the moon
2. Lead low cards early; dump the Queen of Spades the moment you are void in the led suit
3. Watch `points_taken` — if one player is hoovering up everything, they may be shooting the moon; take a trick to stop them
4. Use `self.add_feedback(...)` to debug your strategy in the game output

## Tournament & Ranking
Each game earns placement points (1st = 4, 2nd = 2, 3rd = 1, 4th = 0; ties share).
With up to 20 players every possible table of 4 plays; with more, semi-random
tables are scheduled fairly and your most recent games count for the rankings.
"""

    reward_schema = {
        "kind": "placement",
        "length": 4,
        "labels": ["1st", "2nd", "3rd", "4th"],
        "default": DEFAULT_REWARDS,
    }

    reward_instructions = """## Custom Rewards — Hearts

Placement points awarded per game, best (lowest Hearts score) first.
Default: 1st = **4**, 2nd = **2**, 3rd = **1**, 4th = **0**. Ties share the
mean of the tied placements' points.
"""

    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)
        self.game_feedback = {"game": "hearts", "hands": []}
        self.player_feedback = {}
        self._tournament = None

    # ------------------------------------------------------------- engine

    def _legal_moves(self, hand, trick_plays, first_trick, hearts_broken):
        if not trick_plays:  # leading
            if first_trick:
                return ["2C"]
            if hearts_broken:
                return list(hand)
            non_hearts = [c for c in hand if card_suit(c) != "H"]
            return non_hearts or list(hand)
        led = card_suit(trick_plays[0]["card"])
        follow = [c for c in hand if card_suit(c) == led]
        if follow:
            return follow
        if first_trick:
            clean = [c for c in hand if card_points(c) == 0]
            if clean:
                return clean
        return list(hand)

    def _drain_feedback(self, player):
        if player.feedback:
            lines = [str(m) for m in player.feedback]
            player.feedback = []
            self.player_feedback.setdefault(str(player.name), []).extend(lines)
            return lines
        return None

    def _ask_pass(self, player, hand, direction, hand_number, scores, seat_names):
        state = {
            "phase": "pass",
            "hand": list(hand),
            "pass_direction": direction,
            "hand_number": hand_number,
            "scores": dict(scores),
            "players": list(seat_names),
        }
        try:
            picks = player.make_decision(state)
            picks = list(picks)
        except Exception as e:
            raise ValueError(f"Invalid pass by {player.name}: {e}")
        if len(picks) != 3 or len(set(picks)) != 3 or any(c not in hand for c in picks):
            raise ValueError(
                f"Invalid pass by {player.name}: must be 3 distinct cards "
                f"from your hand, got {picks}"
            )
        return picks

    def _ask_play(self, player, hand, legal, trick_plays, trick_number, leader,
                  hearts_broken, points_taken, scores, seat_names,
                  cards_played, cards_remaining):
        state = {
            "phase": "play",
            "hand": list(hand),
            "legal_moves": list(legal),
            "trick": [dict(p) for p in trick_plays],
            "trick_number": trick_number,
            "leader": leader,
            "hearts_broken": hearts_broken,
            "points_taken": dict(points_taken),
            "scores": dict(scores),
            "players": list(seat_names),
            "cards_played": list(cards_played),
            "cards_remaining": list(cards_remaining),
        }
        try:
            card = player.make_decision(state)
        except Exception as e:
            raise ValueError(f"Invalid move by {player.name}: {e}")
        if card not in legal:
            raise ValueError(
                f"Invalid move by {player.name}: {card} is not one of {legal}"
            )
        return card

    def _play_hand(self, table, hand_number, scores, rng, verbose):
        """Play one 13-trick hand. Returns (hand_record|None, hand_scores, stats)."""
        seat_names = [str(p.name) for p in table]
        deck = DECK[:]
        rng.shuffle(deck)
        hands = {
            str(p.name): sort_hand(deck[i * 13:(i + 1) * 13])
            for i, p in enumerate(table)
        }
        dealt = {n: list(cs) for n, cs in hands.items()} if verbose else None

        direction = PASS_DIRECTIONS[(hand_number - 1) % len(PASS_DIRECTIONS)]
        passes_record = None
        if direction != "hold":
            offset = {"left": 1, "right": -1, "across": 2}[direction]
            targets = {
                seat_names[i]: seat_names[(i + offset) % TABLE_SIZE]
                for i in range(TABLE_SIZE)
            }
            picks = {}
            for p in table:
                name = str(p.name)
                picks[name] = self._ask_pass(
                    p, hands[name], direction, hand_number, scores, seat_names
                )
                self._drain_feedback(p)
            for name, cards in picks.items():
                for c in cards:
                    hands[name].remove(c)
            for name, cards in picks.items():
                hands[targets[name]].extend(cards)
            for name in seat_names:
                hands[name] = sort_hand(hands[name])
            if verbose:
                passes_record = {
                    n: {"to": targets[n], "cards": sort_hand(picks[n])}
                    for n in seat_names
                }
        hands_after_pass = {n: list(cs) for n, cs in hands.items()} if verbose else None

        players_by_name = {str(p.name): p for p in table}
        leader = next(n for n in seat_names if "2C" in hands[n])
        hearts_broken = False
        taken = {n: 0 for n in seat_names}
        queens = {n: 0 for n in seat_names}
        played = []  # every card played this hand, in play order
        tricks_record = [] if verbose else None

        for trick_number in range(1, 14):
            plays = []
            order = [
                seat_names[(seat_names.index(leader) + i) % TABLE_SIZE]
                for i in range(TABLE_SIZE)
            ]
            for name in order:
                player = players_by_name[name]
                legal = self._legal_moves(
                    hands[name], plays, trick_number == 1, hearts_broken
                )
                cards_played = played + [p["card"] for p in plays]
                played_set = set(cards_played)
                cards_remaining = [c for c in DECK if c not in played_set]
                card = self._ask_play(
                    player, hands[name], legal, plays, trick_number, leader,
                    hearts_broken, taken, scores, seat_names,
                    cards_played, cards_remaining,
                )
                hands[name].remove(card)
                if card_suit(card) == "H":
                    hearts_broken = True
                play = {"player": name, "card": card}
                fb = self._drain_feedback(player)
                if verbose and fb:
                    play["feedback"] = fb
                plays.append(play)

            led = card_suit(plays[0]["card"])
            winner = max(
                (p for p in plays if card_suit(p["card"]) == led),
                key=lambda p: card_rank_value(p["card"]),
            )["player"]
            pts = sum(card_points(p["card"]) for p in plays)
            taken[winner] += pts
            played.extend(p["card"] for p in plays)
            if any(p["card"] == "QS" for p in plays):
                queens[winner] += 1
            if verbose:
                tricks_record.append({
                    "trick_number": trick_number,
                    "leader": leader,
                    "plays": plays,
                    "winner": winner,
                    "points": pts,
                    "hearts_broken": hearts_broken,
                })
            leader = winner

        shooter = next((n for n, v in taken.items() if v == 26), None)
        if shooter:
            hand_scores = {n: (0 if n == shooter else 26) for n in seat_names}
        else:
            hand_scores = dict(taken)

        hand_record = None
        if verbose:
            hand_record = {
                "hand_number": hand_number,
                "pass_direction": direction,
                "dealt_hands": dealt,
                "passes": passes_record,
                "hands_after_pass": hands_after_pass,
                "tricks": tricks_record,
                "hand_scores": hand_scores,
                "shot_the_moon": shooter,
            }
        return hand_record, hand_scores, {"queens": queens, "shooter": shooter}

    def _play_table_game(self, table, rng, verbose=False):
        """Play one full game (to TARGET_SCORE) at a table of 4 player objects."""
        seat_names = [str(p.name) for p in table]
        scores = {n: 0 for n in seat_names}
        stats = {
            "hands": 0,
            "hand_points": {n: 0 for n in seat_names},
            "queens": {n: 0 for n in seat_names},
            "moons": {n: 0 for n in seat_names},
        }
        hand_records = [] if verbose else None
        hand_number = 0
        while max(scores.values()) < self.TARGET_SCORE and hand_number < self.MAX_HANDS:
            hand_number += 1
            record, hand_scores, hand_stats = self._play_hand(
                table, hand_number, scores, rng, verbose
            )
            for n in seat_names:
                scores[n] += hand_scores[n]
                stats["hand_points"][n] += hand_scores[n]
                stats["queens"][n] += hand_stats["queens"][n]
            if hand_stats["shooter"]:
                stats["moons"][hand_stats["shooter"]] += 1
            stats["hands"] += 1
            if verbose:
                record["running_scores"] = dict(scores)
                hand_records.append(record)
        winner = min(seat_names, key=lambda n: scores[n])
        return scores, winner, stats, hand_records

    # -------------------------------------------------------------- scoring

    @staticmethod
    def _resolve_rewards(custom_rewards):
        if (
            isinstance(custom_rewards, (list, tuple))
            and len(custom_rewards) == TABLE_SIZE
            and all(isinstance(r, (int, float)) for r in custom_rewards)
        ):
            return list(custom_rewards)
        return list(DEFAULT_REWARDS)

    @staticmethod
    def _placement_points(final_scores, rewards):
        """Placement points, lowest Hearts score first; ties share the mean."""
        ordered = sorted(final_scores.items(), key=lambda kv: kv[1])
        points = {}
        i = 0
        while i < len(ordered):
            j = i
            while j < len(ordered) and ordered[j][1] == ordered[i][1]:
                j += 1
            share = sum(rewards[i:j]) / (j - i)
            for name, _ in ordered[i:j]:
                points[name] = round(share, 2)
            i = j
        return points

    # ---------------------------------------------------------- tournament

    def _roster(self):
        """League players padded to a full table with validation players."""
        roster = list(self.players)
        if len(roster) < TABLE_SIZE:
            module = __import__(
                "backend.games.hearts.validation_players", fromlist=["players"]
            )
            taken_names = {str(p.name) for p in roster}
            for vp in copy.deepcopy(module.players):
                if len(roster) >= TABLE_SIZE:
                    break
                if str(vp.name) in taken_names:
                    vp.name = f"{vp.name}_bot"
                roster.append(vp)
        return roster

    def _ensure_tournament(self):
        if self._tournament is not None:
            return self._tournament
        rng = random.Random()
        roster = self._roster()
        names = [str(p.name) for p in roster]
        state = {
            "rng": rng,
            "roster": roster,
            "by_name": {str(p.name): p for p in roster},
            "exhaustive": len(roster) <= self.EXHAUSTIVE_MAX_PLAYERS,
            "scheduler": None if len(roster) <= self.EXHAUSTIVE_MAX_PLAYERS
            else TableScheduler(names, rng),
            "total_games": 0,
            "games_played": {n: 0 for n in names},
            # sliding window of placement points per player (ranking basis)
            "recent": {n: deque(maxlen=self.RECENT_GAMES_WINDOW) for n in names},
            "reported": {n: 0.0 for n in names},
            "games_won": {n: 0 for n in names},
            "hands_played": {n: 0 for n in names},
            "hand_points": {n: 0 for n in names},
            "moons_shot": {n: 0 for n in names},
            "queens_taken": {n: 0 for n in names},
        }
        self._tournament = state
        return state

    def _next_tables(self, state):
        """The batch of tables for one play_game call, or [] when done."""
        names = list(state["by_name"].keys())
        if state["exhaustive"]:
            # Whole passes only: the first pass always runs (full coverage even
            # if it alone exceeds the budget); later passes must fit.
            tables = list(itertools.combinations(names, TABLE_SIZE))
            played = state["total_games"]
            if played and played + len(tables) > self.MAX_TOTAL_GAMES:
                return []
            state["rng"].shuffle(tables)
            return tables
        if state["total_games"] >= self.MAX_TOTAL_GAMES:
            return []
        if all(
            g >= self.RECENT_GAMES_WINDOW for g in state["games_played"].values()
        ):
            return []
        tables = []
        for _ in range(self.SCHEDULER_ROUNDS_PER_CALL):
            tables.extend(state["scheduler"].next_round())
        remaining = self.MAX_TOTAL_GAMES - state["total_games"]
        return tables[:remaining]

    def play_game(self, custom_rewards=None):
        """Play one tournament batch; None when the tournament is complete."""
        state = self._ensure_tournament()
        rewards = self._resolve_rewards(custom_rewards)
        tables = self._next_tables(state)
        if not tables:
            return None

        for table_names in tables:
            table = [state["by_name"][n] for n in table_names]
            state["rng"].shuffle(table)
            final_scores, winner, stats, _ = self._play_table_game(
                table, state["rng"], verbose=False
            )
            placement = self._placement_points(final_scores, rewards)
            state["total_games"] += 1
            state["games_won"][winner] += 1
            for n in table_names:
                state["games_played"][n] += 1
                state["recent"][n].append(placement[n])
                state["hands_played"][n] += stats["hands"]
                state["hand_points"][n] += stats["hand_points"][n]
                state["moons_shot"][n] += stats["moons"][n]
                state["queens_taken"][n] += stats["queens"][n]

        # Report the change in each player's windowed total: the caller's
        # running sum of these deltas always equals sum(recent games).
        points = {}
        for n, window in state["recent"].items():
            windowed = round(sum(window), 2)
            points[n] = round(windowed - state["reported"][n], 2)
            state["reported"][n] = windowed

        table_stats = {
            "games_won": dict(state["games_won"]),
            "avg_points_per_hand": {
                n: round(state["hand_points"][n] / state["hands_played"][n], 2)
                if state["hands_played"][n]
                else 0
                for n in state["by_name"]
            },
            "moons_shot": dict(state["moons_shot"]),
            "queens_taken": dict(state["queens_taken"]),
            "games_played": dict(state["games_played"]),
        }
        return {
            "points": points,
            "score_aggregate": dict(state["reported"]),
            "table": table_stats,
        }

    def run_simulations(self, num_simulations, league, custom_rewards=None):
        """Validation-path entry point: run the tournament in one call."""
        self._tournament = None
        total_points = {}
        table_stats = {}
        for _ in range(max(1, num_simulations)):
            result = self.play_game(custom_rewards)
            if result is None:
                break
            for n, pts in result["points"].items():
                total_points[n] = round(total_points.get(n, 0) + pts, 2)
            table_stats = result["table"]
        games_played = table_stats.pop("games_played", {})
        return {
            "total_points": total_points,
            "num_simulations": max(games_played.values()) if games_played else 0,
            "table": table_stats,
        }

    # ------------------------------------------------------------- feedback

    def run_single_game_with_feedback(self, custom_rewards=None):
        """One 4-player game with the full hand-by-hand feedback payload."""
        self.verbose = True
        self.player_feedback = {}
        rng = random.Random()
        roster = self._roster()
        table = rng.sample(roster, TABLE_SIZE) if len(roster) > TABLE_SIZE else list(roster)
        rng.shuffle(table)

        final_scores, winner, stats, hand_records = self._play_table_game(
            table, rng, verbose=True
        )
        rewards = self._resolve_rewards(custom_rewards)
        placement = self._placement_points(final_scores, rewards)

        self.game_feedback = {
            "game": "hearts",
            "players": [str(p.name) for p in table],
            "target_score": self.TARGET_SCORE,
            "hands": hand_records,
            "final_scores": final_scores,
            "winner": winner,
        }
        return {
            "results": {
                "points": placement,
                "score_aggregate": placement,
                "table": {},
            },
            "feedback": self.game_feedback,
            "player_feedback": self.player_feedback,
        }

    def reset(self):
        """Reset per-call scores/feedback but keep the tournament running."""
        tournament = self._tournament
        super().reset()
        self.game_feedback = {"game": "hearts", "hands": []}
        self.player_feedback = {}
        self._tournament = tournament
