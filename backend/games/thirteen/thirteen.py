"""Thirteen (Tiến lên) — an individual 4-player climbing/shedding game where the
order in which players empty their hands *is* the placement (first out = 1st).

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

Scoring: placement points per game (default 4/2/1/0). Finish order is a strict
ordering of the four seats, so there are no ties — the i-th player to shed all
its cards takes reward slot i.

Ruleset (a deliberately trimmed Tiến lên):
- Combos: single, pair, triple, straight (>=3 consecutive ranks, no 2), and one
  bomb = four-of-a-kind.
- Beat a pile with the same shape + same length, strictly higher — or pass. A
  four-of-a-kind bomb also beats a single 2 / a pair of 2s / a lower bomb.
- The holder of the single lowest card leads the first pile with any legal combo;
  thereafter whoever wins a pile (all others pass) leads a fresh combo.
"""

import copy
import itertools
import random
from collections import deque

from backend.games.base_game import BaseGame

# Rank order runs 3 (lowest) .. 2 (highest); suits break ties S < C < D < H.
RANKS = ["3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2"]
RANK_VALUE = {r: i for i, r in enumerate(RANKS, start=3)}  # 3->3 .. 2->15
SUITS = ["S", "C", "D", "H"]
SUIT_VALUE = {s: i for i, s in enumerate(SUITS)}  # S->0 .. H->3
DECK = [r + s for s in SUITS for r in RANKS]

TABLE_SIZE = 4
HAND_SIZE = 13
DEFAULT_REWARDS = [4, 2, 1, 0]  # placement points for 1st..4th to finish
TWO = RANK_VALUE["2"]


def card_suit(card):
    return card[-1]


def card_rank(card):
    return RANK_VALUE[card[:-1]]


def card_key(card):
    """Total order on cards: rank first, then suit."""
    return (card_rank(card), SUIT_VALUE[card_suit(card)])


def sort_hand(cards):
    return sorted(cards, key=card_key)


def classify(combo):
    """Return (kind, length, top_key) for a legal combo, else None.

    kind is one of "single", "pair", "triple", "bomb", "straight". top_key is the
    card_key of the highest card and is how two same-shape combos are compared.
    """
    if not combo:
        return None
    cards = list(combo)
    if len(set(cards)) != len(cards):
        return None  # duplicate card codes are never a legal combo
    n = len(cards)
    ranks = [card_rank(c) for c in cards]
    top_key = max(card_key(c) for c in cards)

    if len(set(ranks)) == 1:  # all the same rank
        return {1: ("single", 1, top_key),
                2: ("pair", 2, top_key),
                3: ("triple", 3, top_key),
                4: ("bomb", 4, top_key)}.get(n)

    if n >= 3:  # candidate straight
        if any(r == TWO for r in ranks):
            return None  # 2s can't appear in a straight
        rs = sorted(ranks)
        if len(set(rs)) == n and rs[-1] - rs[0] == n - 1:
            return ("straight", n, top_key)
    return None


def _all_twos(combo):
    return all(card_rank(c) == TWO for c in combo)


def beats(cand, pile):
    """Does combo `cand` legally beat combo `pile`?"""
    c = classify(cand)
    p = classify(pile)
    if c is None or p is None:
        return False
    ckind, clen, ckey = c
    pkind, plen, pkey = p

    if ckind == "bomb":
        if pkind == "bomb":
            return ckey > pkey  # higher four-of-a-kind
        if pkind in ("single", "pair") and _all_twos(pile):
            return True  # bomb chops a single 2 or a pair of 2s
        return False

    return ckind == pkind and clen == plen and ckey > pkey


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


class ThirteenGame(BaseGame):
    EXHAUSTIVE_MAX_PLAYERS = 20
    RECENT_GAMES_WINDOW = 500
    SCHEDULER_ROUNDS_PER_CALL = 5
    MAX_TOTAL_GAMES = 6000

    starter_code = """
from games.thirteen.player import Player
import random

class CustomPlayer(Player):
    def make_decision(self, game_state):
        # Card codes are rank + suit letter: "3S", "10H", "2C". In Thirteen 3 is
        # the LOWEST rank and 2 is the HIGHEST; suits rank S < C < D < H.

        legal_moves = game_state["legal_moves"]  # list of combos you may play;
                                                 # [] (pass) is included unless leading
        hand = game_state["hand"]                # your remaining cards
        leading = game_state["leading"]          # True = you start a fresh pile
        pile = game_state["pile"]                # the combo you must beat ([] when leading)
        pile_owner = game_state["pile_owner"]    # who laid the current pile (or None)
        hand_sizes = game_state["hand_sizes"]    # cards left per player {name: n}
        players = game_state["players"]          # seat order
        finished = game_state["finished"]        # players already out, in finish order
        passed = game_state["passed"]            # players who have passed this pile

        self.add_feedback(f"leading={leading} pile={pile} choices={len(legal_moves)}")

        return random.choice(legal_moves)  # fallback: a random legal combo (or pass)
"""

    game_instructions = """
# Thirteen (Tiến lên) Instructions

An individual **shedding** game for 4 players: be the first to get rid of all 13
of your cards. The order in which the four players empty their hands is the
finishing order — 1st out places 1st, and so on.

## Game Objective
Empty your hand before everyone else. Each game awards placement points
(1st = 4, 2nd = 2, 3rd = 1, 4th = 0). There is no running score to minimise or
maximise — only how quickly you shed relative to the table.

## Card ranking
Ranks run from **3 (lowest) up to 2 (highest)**: 3 < 4 < ... < K < A < 2. When
two cards share a rank, suits break the tie: **♠ < ♣ < ♦ < ♥**. So `2H` is the
single strongest card and `3S` the weakest.

## Combinations
You play cards in *combos*; the pile can only be beaten by the same shape:
- **Single** — one card
- **Pair** — two cards of the same rank
- **Triple** — three cards of the same rank
- **Straight** — three or more consecutive ranks (any suits), e.g. `4-5-6`. A
  straight can **not** contain a 2.
- **Bomb** — four of a kind. A bomb beats a single 2, a pair of 2s, or a lower
  bomb (this is the only time a combo of one shape beats another).

## Game Rules
- All 52 cards are dealt, 13 each. The player holding the single **lowest card**
  leads the first pile and may lead any legal combo.
- Going clockwise, each player either **beats** the current pile (same shape and
  length, strictly higher) or **passes**. Once everyone else passes, the player
  who laid the pile wins it, clears the table, and leads a fresh combo of any
  shape.
- Play continues until only one player has cards left; that player finishes 4th.

## Your Task
Implement `make_decision(game_state)`. Return **one combo** — a list of card
codes — chosen from `game_state["legal_moves"]`, or the empty list `[]` to pass.
When `game_state["leading"]` is True you must lead (passing is not offered).

Card codes are rank + suit letter: `"3S"`, `"10H"`, `"2C"`.

## Available Information
In the `game_state` dictionary:
- `legal_moves`: every combo you may play right now (each a list of card codes);
  includes `[]` (pass) unless you are leading
- `hand`: your remaining cards; `leading`: are you starting a fresh pile?
- `pile`: the combo to beat (`[]` when leading); `pile_owner`: who laid it
- `hand_sizes`: cards left per player `{name: n}`; `players`: seat order
- `finished`: players already out, in finish order; `passed`: who has passed on
  the current pile

## Strategy Tips
1. Shed your weakest cards first — low singles and awkward leftovers — while you
   still control the lead
2. Hoard your 2s and your bomb: they are your tempo. A saved 2 wins a pile late
   and hands you a free fresh lead
3. Don't break a pair, triple, or bomb just to answer a single — you usually lose
   more than you gain; passing is often the strongest move
4. Shape your hand into combos you can dump in one turn (a long straight sheds
   many cards at once)
5. Use `self.add_feedback(...)` to debug your strategy in the game output

## Tournament & Ranking
Each game earns placement points (1st = 4, 2nd = 2, 3rd = 1, 4th = 0). With up to
20 players every possible table of 4 plays; with more, semi-random tables are
scheduled fairly and your most recent games count for the rankings.
"""

    reward_schema = {
        "kind": "placement",
        "length": 4,
        "labels": ["1st", "2nd", "3rd", "4th"],
        "default": DEFAULT_REWARDS,
    }

    reward_instructions = """## Custom Rewards — Thirteen

Placement points awarded per game by finishing order (first player to empty their
hand first). Default: 1st = **4**, 2nd = **2**, 3rd = **1**, 4th = **0**.
"""

    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)
        self.game_feedback = {"game": "thirteen", "plays": []}
        self.player_feedback = {}
        self._tournament = None

    # ------------------------------------------------------------- combos

    def _rank_groups(self, hand):
        groups = {}
        for c in hand:
            groups.setdefault(card_rank(c), []).append(c)
        return groups

    def _same_rank_combos(self, hand, size):
        out = []
        for cs in self._rank_groups(hand).values():
            if len(cs) >= size:
                for combo in itertools.combinations(sort_hand(cs), size):
                    out.append(list(combo))
        return out

    def _straights(self, hand, length=None):
        by_rank = self._rank_groups(hand)
        present = sorted(r for r in by_rank if r != TWO)
        if not present:
            return []
        lengths = [length] if length else range(3, len(present) + 1)
        out = []
        for L in lengths:
            if L < 3:
                continue
            for start in present:
                window = list(range(start, start + L))
                if window[-1] >= TWO:
                    break  # a straight can't reach the 2s
                if all(r in by_rank for r in window):
                    choices = [sort_hand(by_rank[r]) for r in window]
                    for combo in itertools.product(*choices):
                        out.append(sort_hand(list(combo)))
        return out

    @staticmethod
    def _dedupe(combos):
        seen = {}
        for m in combos:
            key = tuple(sort_hand(m))
            if key not in seen:
                seen[key] = list(key)
        return list(seen.values())

    def _legal_leads(self, hand):
        combos = [[c] for c in sort_hand(hand)]
        for size in (2, 3, 4):
            combos += self._same_rank_combos(hand, size)
        combos += self._straights(hand)
        return self._dedupe(combos)

    def _legal_responses(self, hand, pile):
        kind, length, _ = classify(pile)
        moves = []
        if kind == "bomb":
            moves += self._same_rank_combos(hand, 4)  # only a higher bomb beats
        else:
            if kind in ("single", "pair") and _all_twos(pile):
                moves += self._same_rank_combos(hand, 4)  # bomb chops the 2s
            if kind == "single":
                moves += [[c] for c in hand]
            elif kind == "pair":
                moves += self._same_rank_combos(hand, 2)
            elif kind == "triple":
                moves += self._same_rank_combos(hand, 3)
            elif kind == "straight":
                moves += self._straights(hand, length)
        moves = [m for m in moves if beats(m, pile)]
        moves = self._dedupe(moves)
        moves.append([])  # pass is always legal when responding
        return moves

    # -------------------------------------------------------------- engine

    def _drain_feedback(self, player):
        if player.feedback:
            lines = [str(m) for m in player.feedback]
            player.feedback = []
            self.player_feedback.setdefault(str(player.name), []).extend(lines)
            return lines
        return None

    def _ask_play(self, player, hand, legal, leading, pile, pile_owner,
                  seat_names, hand_sizes, finished, passed):
        state = {
            "phase": "play",
            "hand": list(hand),
            "legal_moves": [list(m) for m in legal],
            "leading": leading,
            "pile": list(pile),
            "pile_owner": pile_owner,
            "players": list(seat_names),
            "hand_sizes": dict(hand_sizes),
            "finished": list(finished),
            "passed": list(passed),
        }
        try:
            move = list(player.make_decision(state))
        except Exception as e:
            raise ValueError(f"Invalid move by {player.name}: {e}")
        legal_set = {tuple(sort_hand(m)) for m in legal}
        try:
            move_key = tuple(sort_hand(move))
        except (KeyError, TypeError, IndexError):
            move_key = None  # unparseable card codes are never legal
        if move_key not in legal_set:
            raise ValueError(
                f"Invalid move by {player.name}: {move} is not one of {legal}"
            )
        return list(move_key)

    def _play_deal(self, table, rng, verbose):
        """Play one full deal. Returns (finish_order, winner, stats, record)."""
        seat_names = [str(p.name) for p in table]
        by_name = {str(p.name): p for p in table}
        deck = DECK[:]
        rng.shuffle(deck)
        hands = {
            seat_names[i]: sort_hand(deck[i * HAND_SIZE:(i + 1) * HAND_SIZE])
            for i in range(TABLE_SIZE)
        }
        dealt = {n: list(cs) for n, cs in hands.items()} if verbose else None

        finish_order = []
        bombs = {n: 0 for n in seat_names}
        plays = [] if verbose else None
        seq = 0

        lowest = min((c for cs in hands.values() for c in cs), key=card_key)
        turn = next(i for i, n in enumerate(seat_names) if lowest in hands[n])

        pile = []
        pile_owner = None
        passed = set()
        passes = 0
        fresh = True

        def hand_sizes():
            return {n: len(hands[n]) for n in seat_names}

        while len(finish_order) < TABLE_SIZE - 1:
            name = seat_names[turn]
            if name in finish_order:
                turn = (turn + 1) % TABLE_SIZE
                continue

            leading = fresh
            legal = (
                self._legal_leads(hands[name])
                if leading
                else self._legal_responses(hands[name], pile)
            )
            move = self._ask_play(
                by_name[name], hands[name], legal, leading, pile, pile_owner,
                seat_names, hand_sizes(), finish_order, sorted(passed),
            )
            fb = self._drain_feedback(by_name[name])
            seq += 1

            cleared = False
            if move == []:  # pass (only possible when not leading)
                passed.add(name)
                passes += 1
            else:
                for c in move:
                    hands[name].remove(c)
                if classify(move)[0] == "bomb":
                    bombs[name] += 1
                pile = move
                pile_owner = name
                passed = set()
                passes = 0
                fresh = False
                if not hands[name]:
                    finish_order.append(name)

            active = [n for n in seat_names if n not in finish_order]
            others = len(active) - (1 if pile_owner in active else 0)
            if not fresh and (others <= 0 or passes >= others):
                # Everyone still in has passed on the pile: its owner (or, if the
                # owner has gone out, the next active seat) leads a fresh combo.
                if pile_owner in active:
                    leader = pile_owner
                else:
                    k = seat_names.index(pile_owner)
                    leader = next(
                        seat_names[(k + i) % TABLE_SIZE]
                        for i in range(1, TABLE_SIZE + 1)
                        if seat_names[(k + i) % TABLE_SIZE] in active
                    )
                cleared = True

            if verbose:
                plays.append({
                    "seq": seq,
                    "seat": name,
                    "action": "pass" if move == [] else "play",
                    "combo": None if move == [] else list(move),
                    "fresh_lead": leading,
                    "pile_after": list(pile),
                    "hand_size_after": len(hands[name]),
                    "cleared": cleared,
                    **({"feedback": fb} if fb else {}),
                })

            if cleared:
                turn = seat_names.index(leader)
                pile = []
                pile_owner = None
                passed = set()
                passes = 0
                fresh = True
            else:
                turn = (turn + 1) % TABLE_SIZE

        last = next(n for n in seat_names if n not in finish_order)
        finish_order.append(last)

        winner = finish_order[0]
        stats = {
            "finish_pos": {n: finish_order.index(n) + 1 for n in seat_names},
            "bombs": bombs,
        }
        record = None
        if verbose:
            record = {
                "dealt_hands": dealt,
                "plays": plays,
                "finish_order": list(finish_order),
            }
        return finish_order, winner, stats, record

    def _play_table_game(self, table, rng, verbose=False):
        """Play one full game (a single deal) at a table of 4 player objects."""
        return self._play_deal(table, rng, verbose)

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
    def _placement_points(finish_order, rewards):
        """Placement points by finishing order; first player out takes slot 0."""
        return {name: rewards[i] for i, name in enumerate(finish_order)}

    # ---------------------------------------------------------- tournament

    def _roster(self):
        """League players padded to a full table with validation players."""
        roster = list(self.players)
        if len(roster) < TABLE_SIZE:
            module = __import__(
                "backend.games.thirteen.validation_players", fromlist=["players"]
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
            "finish_sum": {n: 0 for n in names},
            "bombs": {n: 0 for n in names},
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
            finish_order, winner, stats, _ = self._play_table_game(
                table, state["rng"], verbose=False
            )
            placement = self._placement_points(finish_order, rewards)
            state["total_games"] += 1
            state["games_won"][winner] += 1
            for n in table_names:
                state["games_played"][n] += 1
                state["recent"][n].append(placement[n])
                state["finish_sum"][n] += stats["finish_pos"][n]
                state["bombs"][n] += stats["bombs"][n]

        # Report the change in each player's windowed total: the caller's
        # running sum of these deltas always equals sum(recent games).
        points = {}
        for n, window in state["recent"].items():
            windowed = round(sum(window), 2)
            points[n] = round(windowed - state["reported"][n], 2)
            state["reported"][n] = windowed

        table_stats = {
            "games_won": dict(state["games_won"]),
            "avg_finish": {
                n: round(state["finish_sum"][n] / state["games_played"][n], 2)
                if state["games_played"][n]
                else 0
                for n in state["by_name"]
            },
            "bombs_played": dict(state["bombs"]),
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
        """One 4-player deal with the full play-by-play feedback payload."""
        self.verbose = True
        self.player_feedback = {}
        rng = random.Random()
        roster = self._roster()
        table = rng.sample(roster, TABLE_SIZE) if len(roster) > TABLE_SIZE else list(roster)
        rng.shuffle(table)

        finish_order, winner, _, record = self._play_table_game(
            table, rng, verbose=True
        )
        rewards = self._resolve_rewards(custom_rewards)
        placement = self._placement_points(finish_order, rewards)

        self.game_feedback = {
            "game": "thirteen",
            "players": [str(p.name) for p in table],
            "dealt_hands": record["dealt_hands"],
            "plays": record["plays"],
            "finish_order": finish_order,
            "placements": {n: finish_order.index(n) + 1 for n in finish_order},
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
        self.game_feedback = {"game": "thirteen", "plays": []}
        self.player_feedback = {}
        self._tournament = tournament
