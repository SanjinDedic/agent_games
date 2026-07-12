"""Oh Hell! — the trick-taking game where you must win *exactly* the number of
tricks you bid, played at tables of 4.

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

Scoring: placement points per game (default 4/2/1/0, ties share the mean). The
raw Oh Hell score (highest wins) only feeds placements and the per-round stats.
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
DEFAULT_REWARDS = [4, 2, 1, 0]  # placement points for 1st..4th (highest score first)
BID_BONUS = 10  # bonus for taking exactly the number of tricks you bid

# Cards dealt each round. Descending 10 -> 1 (a common short Oh Hell variant);
# with 4 players the top of the remaining stub is flipped for trump, so the
# deal must stay at 12 cards or fewer.
DEAL_SEQUENCE = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]

SUIT_NAMES = {"C": "Clubs", "D": "Diamonds", "S": "Spades", "H": "Hearts"}


def card_suit(card):
    return card[-1]


def card_rank_value(card):
    return RANK_VALUE[card[:-1]]


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


class OhHellGame(BaseGame):
    EXHAUSTIVE_MAX_PLAYERS = 20
    RECENT_GAMES_WINDOW = 500
    SCHEDULER_ROUNDS_PER_CALL = 5
    MAX_TOTAL_GAMES = 6000

    # Benchmarked: ~16ms per pass (each pass fans out into many sub-games)
    # keeps validation <1s.
    validation_simulations = 40

    starter_code = """
from games.ohhell.player import Player
import random

class CustomPlayer(Player):
    def make_decision(self, game_state):
        # Card codes are rank + suit letter: "QS", "10H", "2C", "AD"

        # ---- available in BOTH phases -----------------------------------
        phase = game_state["phase"]          # "bid" or "play"
        hand = game_state["hand"]            # your current cards (list of codes)
        trump = game_state["trump"]          # trump suit letter: "C"/"D"/"S"/"H"
        cards_this_round = game_state["cards_this_round"]  # tricks available this round
        round_number = game_state["round_number"]          # which round of the game
        scores = game_state["scores"]        # running game score per player {name: points}
        players = game_state["players"]      # seat order, list of player names

        if phase == "bid":
            # ---- available only in the BID phase ------------------------
            bids_so_far = game_state["bids_so_far"]   # [{"player", "bid"}, ...] before you
            forbidden_bid = game_state["forbidden_bid"]  # int you may NOT bid, or None
            trump_card = game_state["trump_card"]     # the flipped card that set trump

            self.add_feedback(f"Round {round_number}: {cards_this_round} cards, trump {trump}, hand {hand}")

            # Bid a random number of tricks you promise to take (0..cards_this_round),
            # avoiding the forbidden bid if you are last to bid.
            choices = [b for b in range(cards_this_round + 1) if b != forbidden_bid]
            return random.choice(choices)

        # ---- available only in the PLAY phase ---------------------------
        legal_moves = game_state["legal_moves"]   # cards you may play right now
        trick = game_state["trick"]               # this trick so far: [{"player", "card"}, ...]
        trick_number = game_state["trick_number"] # 1..cards_this_round
        leader = game_state["leader"]             # name of who led this trick
        bids = game_state["bids"]                 # everyone's bid this round {name: bid}
        tricks_won = game_state["tricks_won"]     # tricks each player has won THIS round {name: n}
        cards_played = game_state["cards_played"]     # every card played this round so far (in order)
        cards_remaining = game_state["cards_remaining"]  # dealt cards not yet played (includes your hand)

        self.add_feedback(f"Trick {trick_number}: choosing from {legal_moves} "
                          f"(bid {bids[self.name]}, won {tricks_won[self.name]})")

        return random.choice(legal_moves)  # fallback to random legal card
"""

    game_instructions = """
# Oh Hell! Game Instructions

The trick-taking game where the goal is to win **exactly** the number of tricks
you bid — no more, no fewer. Played at tables of 4.

**New to Oh Hell?** Play a few rounds yourself at
[cardgames.io/ohhell](https://cardgames.io/ohhell/) — it is the fastest way to
get the rules to click before you start coding your agent.

## Game Objective
Score as many points as possible across the game's rounds. Each round you take
tricks worth 1 point each, plus a **10-point bonus if you take exactly as many
tricks as you bid**. Miss your bid — over or under — and you get the trick
points only, no bonus. The player with the most points at the end wins the table.

## What is a trick?
A **trick** is one round where each of the 4 players plays a single card, in
seat order. The first player "leads" a card, setting the **led suit**; the other
three follow in turn. The highest **trump** wins, or if no trump was played, the
highest card *of the led suit*. The winner collects the trick and leads next.

## Game Rules
- The game is a sequence of rounds. Round 1 deals 10 cards each, and each later
  round deals one fewer, down to 1 card (10, 9, 8, ... 1)
- After the deal, the top card of the remaining stack is flipped — its suit is
  **trump** for the round
- **Bidding:** in seat order (dealer bids last), each player states how many
  tricks they will take, 0 up to the number of cards dealt. The dealer's bid is
  constrained so the bids can never total exactly the number of tricks —
  somebody is always forced to miss (`forbidden_bid` tells you the banned value)
- **Play:** the player left of the dealer leads the first trick. You must follow
  the led suit if you can; if you are void, play anything (including trump).
  Trump does not need to be "broken" — it may be led at any time
- Each trick you win is 1 point; hitting your bid exactly adds a 10-point bonus

## Your Task
Implement `make_decision(game_state)`; it is called for both phases:
- `game_state["phase"] == "bid"` → return an integer 0..`cards_this_round`
- `game_state["phase"] == "play"` → return one card code from `game_state["legal_moves"]`

Card codes are rank + suit letter: `"QS"`, `"10H"`, `"2C"`, `"AD"`.

## Available Information
In the `game_state` dictionary:
- `phase`: `"bid"` or `"play"`
- `hand`: your current cards
- `trump`: the trump suit letter (`"C"`/`"D"`/`"S"`/`"H"`)
- `cards_this_round`: tricks available this round; `round_number`
- `scores`: running game scores; `players`: seat order
- Bid phase only: `bids_so_far` (`[{"player", "bid"}, ...]` before you),
  `forbidden_bid` (the value you may not bid, or `None`), `trump_card`,
  `dealer`
- Play phase only: `legal_moves`, `trick` (cards played so far this trick),
  `trick_number` (1..cards_this_round), `leader`, `bids` (everyone's bid),
  `tricks_won` (tricks each player has taken this round), `cards_played` (every
  card played this round so far, in order), `cards_remaining` (dealt cards not
  yet played, including your own hand)

## Strategy Tips
1. Bid from your high cards: aces and high trumps are near-certain tricks; count
   your trumps and top cards to estimate how many tricks you can force
2. Once you have your bid, **play to hit it exactly** — if you still need tricks,
   win them; once you have enough, deliberately duck (play low, dump losers)
3. Watch `bids` vs `tricks_won`: a player who has already made their bid wants to
   lose the rest, so you can often hand them tricks — or dodge ones you don't want
4. Leading trump flushes out opponents' trumps; hold a trump to steal a trick you
   need late in the round
5. Use `self.add_feedback(...)` to debug your strategy in the game output

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

    reward_instructions = """## Custom Rewards — Oh Hell!

Placement points awarded per game, best (highest Oh Hell score) first.
Default: 1st = **4**, 2nd = **2**, 3rd = **1**, 4th = **0**. Ties share the
mean of the tied placements' points.
"""

    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)
        self.game_feedback = {"game": "ohhell", "rounds": []}
        self.player_feedback = {}
        self._tournament = None

    # ------------------------------------------------------------- engine

    def _legal_moves(self, hand, trick_plays):
        if not trick_plays:  # leading — anything goes (trump need not be broken)
            return list(hand)
        led = card_suit(trick_plays[0]["card"])
        follow = [c for c in hand if card_suit(c) == led]
        return follow or list(hand)

    def _trick_winner(self, plays, trump):
        led = card_suit(plays[0]["card"])
        trumps = [p for p in plays if card_suit(p["card"]) == trump]
        pool = trumps if trumps else [p for p in plays if card_suit(p["card"]) == led]
        return max(pool, key=lambda p: card_rank_value(p["card"]))["player"]

    def _drain_feedback(self, player):
        if player.feedback:
            lines = [str(m) for m in player.feedback]
            player.feedback = []
            self.player_feedback.setdefault(str(player.name), []).extend(lines)
            return lines
        return None

    def _ask_bid(self, player, hand, trump, trump_card, cards, round_number,
                 bids_so_far, forbidden, dealer, scores, seat_names):
        state = {
            "phase": "bid",
            "hand": list(hand),
            "trump": trump,
            "trump_card": trump_card,
            "cards_this_round": cards,
            "round_number": round_number,
            "bids_so_far": [dict(b) for b in bids_so_far],
            "forbidden_bid": forbidden,
            "dealer": dealer,
            "scores": dict(scores),
            "players": list(seat_names),
        }
        try:
            bid = int(player.make_decision(state))
        except Exception as e:
            raise ValueError(f"Invalid bid by {player.name}: {e}")
        if bid < 0 or bid > cards:
            raise ValueError(
                f"Invalid bid by {player.name}: {bid} is not between 0 and {cards}"
            )
        if forbidden is not None and bid == forbidden:
            raise ValueError(
                f"Invalid bid by {player.name}: {bid} is forbidden (the bids "
                f"would total the number of tricks)"
            )
        return bid

    def _ask_play(self, player, hand, legal, trump, trick_plays, trick_number,
                  leader, bids, tricks_won, scores, seat_names,
                  cards_played, cards_remaining, cards, round_number):
        state = {
            "phase": "play",
            "hand": list(hand),
            "legal_moves": list(legal),
            "trump": trump,
            "trick": [dict(p) for p in trick_plays],
            "trick_number": trick_number,
            "leader": leader,
            "bids": dict(bids),
            "tricks_won": dict(tricks_won),
            "cards_this_round": cards,
            "round_number": round_number,
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

    def _play_round(self, table, round_number, cards, scores, rng, verbose):
        """Play one round of `cards` tricks. Returns (record|None, round_scores, stats)."""
        seat_names = [str(p.name) for p in table]
        players_by_name = {str(p.name): p for p in table}
        deck = DECK[:]
        rng.shuffle(deck)
        hands = {
            seat_names[i]: sort_hand(deck[i * cards:(i + 1) * cards])
            for i in range(TABLE_SIZE)
        }
        trump_card = deck[TABLE_SIZE * cards]
        trump = card_suit(trump_card)
        dealt_all = [c for name in seat_names for c in hands[name]]
        dealt = {n: list(cs) for n, cs in hands.items()} if verbose else None

        dealer_idx = (round_number - 1) % TABLE_SIZE
        first_idx = (dealer_idx + 1) % TABLE_SIZE
        dealer = seat_names[dealer_idx]
        bid_order = [seat_names[(first_idx + i) % TABLE_SIZE] for i in range(TABLE_SIZE)]

        bids = {}
        for i, name in enumerate(bid_order):
            is_last = i == TABLE_SIZE - 1
            forbidden = None
            if is_last:
                needed = cards - sum(bids.values())
                if 0 <= needed <= cards:
                    forbidden = needed
            bids_so_far = [{"player": n, "bid": bids[n]} for n in bid_order[:i]]
            bids[name] = self._ask_bid(
                players_by_name[name], hands[name], trump, trump_card, cards,
                round_number, bids_so_far, forbidden, dealer, scores, seat_names,
            )
            self._drain_feedback(players_by_name[name])

        leader = seat_names[first_idx]
        tricks_won = {n: 0 for n in seat_names}
        played = []  # every card played this round, in play order
        tricks_record = [] if verbose else None

        for trick_number in range(1, cards + 1):
            plays = []
            order = [
                seat_names[(seat_names.index(leader) + i) % TABLE_SIZE]
                for i in range(TABLE_SIZE)
            ]
            for name in order:
                player = players_by_name[name]
                legal = self._legal_moves(hands[name], plays)
                cards_played = played + [p["card"] for p in plays]
                played_set = set(cards_played)
                cards_remaining = [c for c in dealt_all if c not in played_set]
                card = self._ask_play(
                    player, hands[name], legal, trump, plays, trick_number, leader,
                    bids, tricks_won, scores, seat_names, cards_played, cards_remaining,
                    cards, round_number,
                )
                hands[name].remove(card)
                play = {"player": name, "card": card}
                fb = self._drain_feedback(player)
                if verbose and fb:
                    play["feedback"] = fb
                plays.append(play)

            winner = self._trick_winner(plays, trump)
            tricks_won[winner] += 1
            played.extend(p["card"] for p in plays)
            if verbose:
                tricks_record.append({
                    "trick_number": trick_number,
                    "leader": leader,
                    "plays": plays,
                    "winner": winner,
                })
            leader = winner

        round_scores = {}
        hit = {}
        for n in seat_names:
            made = tricks_won[n] == bids[n]
            round_scores[n] = tricks_won[n] + (BID_BONUS if made else 0)
            hit[n] = made

        record = None
        if verbose:
            record = {
                "round_number": round_number,
                "cards": cards,
                "trump": trump,
                "trump_card": trump_card,
                "dealer": dealer,
                "dealt_hands": dealt,
                "bids": dict(bids),
                "tricks": tricks_record,
                "tricks_won": dict(tricks_won),
                "round_scores": dict(round_scores),
            }
        return record, round_scores, {"bids_hit": hit}

    def _play_table_game(self, table, rng, verbose=False):
        """Play one full game (all rounds in DEAL_SEQUENCE) at a table of 4."""
        seat_names = [str(p.name) for p in table]
        scores = {n: 0 for n in seat_names}
        stats = {
            "rounds": 0,
            "round_score": {n: 0 for n in seat_names},
            "bids_hit": {n: 0 for n in seat_names},
        }
        round_records = [] if verbose else None
        for round_number, cards in enumerate(DEAL_SEQUENCE, start=1):
            record, round_scores, round_stats = self._play_round(
                table, round_number, cards, scores, rng, verbose
            )
            for n in seat_names:
                scores[n] += round_scores[n]
                stats["round_score"][n] += round_scores[n]
                stats["bids_hit"][n] += 1 if round_stats["bids_hit"][n] else 0
            stats["rounds"] += 1
            if verbose:
                record["running_scores"] = dict(scores)
                round_records.append(record)
        winner = max(seat_names, key=lambda n: scores[n])
        return scores, winner, stats, round_records

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
        """Placement points, highest Oh Hell score first; ties share the mean."""
        ordered = sorted(final_scores.items(), key=lambda kv: -kv[1])
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
                "backend.games.ohhell.validation_players", fromlist=["players"]
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
            "rounds_played": {n: 0 for n in names},
            "round_points": {n: 0 for n in names},
            "bids_hit": {n: 0 for n in names},
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
                state["rounds_played"][n] += stats["rounds"]
                state["round_points"][n] += stats["round_score"][n]
                state["bids_hit"][n] += stats["bids_hit"][n]

        # Report the change in each player's windowed total: the caller's
        # running sum of these deltas always equals sum(recent games).
        points = {}
        for n, window in state["recent"].items():
            windowed = round(sum(window), 2)
            points[n] = round(windowed - state["reported"][n], 2)
            state["reported"][n] = windowed

        table_stats = {
            "games_won": dict(state["games_won"]),
            "bid_accuracy": {
                n: round(state["bids_hit"][n] / state["rounds_played"][n], 3)
                if state["rounds_played"][n]
                else 0
                for n in state["by_name"]
            },
            "avg_round_score": {
                n: round(state["round_points"][n] / state["rounds_played"][n], 2)
                if state["rounds_played"][n]
                else 0
                for n in state["by_name"]
            },
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
        """One 4-player game with the full round-by-round feedback payload."""
        self.verbose = True
        self.player_feedback = {}
        rng = random.Random()
        roster = self._roster()
        table = rng.sample(roster, TABLE_SIZE) if len(roster) > TABLE_SIZE else list(roster)
        rng.shuffle(table)

        final_scores, winner, stats, round_records = self._play_table_game(
            table, rng, verbose=True
        )
        rewards = self._resolve_rewards(custom_rewards)
        placement = self._placement_points(final_scores, rewards)

        self.game_feedback = {
            "game": "ohhell",
            "players": [str(p.name) for p in table],
            "rounds": round_records,
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
        self.game_feedback = {"game": "ohhell", "rounds": []}
        self.player_feedback = {}
        self._tournament = tournament
