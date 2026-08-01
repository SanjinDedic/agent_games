import random

from backend.games.thirteen.player import Player
from backend.games.thirteen.thirteen import TWO, card_rank, classify


def _combo_key(combo):
    """Sort key for a non-empty combo: highest card first, then length."""
    _kind, length, top = classify(combo)
    return (top, length)


def _uses_control(combo):
    """True if the combo spends a 2 or a four-of-a-kind bomb (tempo cards)."""
    return classify(combo)[0] == "bomb" or any(card_rank(c) == TWO for c in combo)


class Controller(Player):
    """Hoards 2s and its bomb: sheds cheap combos while it leads, passes rather
    than spend a control card, and only cracks a 2/bomb open near the endgame to
    seize tempo. The strongest of the validation bots."""

    strategy = (
        "Hoards its 2s and bombs, shedding cheap combos and passing rather "
        "than spend a control card — only cracks them open near the endgame "
        "to seize tempo. The strongest validation bot."
    )

    def make_decision(self, game_state):
        legal = game_state["legal_moves"]
        plays = [m for m in legal if m]
        can_pass = [] in legal

        opp_min = min(
            (v for p, v in game_state["hand_sizes"].items() if p != self.name),
            default=99,
        )
        endgame = len(game_state["hand"]) <= 5 or opp_min <= 2

        if game_state["leading"]:
            safe = [m for m in plays if not _uses_control(m)]
            self.add_feedback("lead")
            return min(safe or plays, key=_combo_key)

        cheap = [m for m in plays if not _uses_control(m)]
        if cheap:
            return min(cheap, key=_combo_key)
        if endgame and plays:
            self.add_feedback("spend control for tempo")
            return min(plays, key=_combo_key)
        return [] if can_pass else min(plays, key=_combo_key)


class LowballShedder(Player):
    """Always plays its lowest legal combo, but never breaks a pair/triple/bomb
    just to answer a single — it passes instead."""

    strategy = (
        "Always plays its lowest legal combo, but never breaks up a "
        "pair, triple or bomb just to answer a single — it passes instead."
    )

    def make_decision(self, game_state):
        legal = game_state["legal_moves"]
        hand = game_state["hand"]
        plays = [m for m in legal if m]
        can_pass = [] in legal

        counts = {}
        for c in hand:
            counts[card_rank(c)] = counts.get(card_rank(c), 0) + 1

        def breaks_set(combo):
            return len(combo) == 1 and counts.get(card_rank(combo[0]), 0) >= 2

        keep = [m for m in plays if not breaks_set(m)]
        if game_state["leading"]:
            return min(keep or plays, key=_combo_key)
        if keep:
            return min(keep, key=_combo_key)
        return [] if can_pass else min(plays, key=_combo_key)


class Beater(Player):
    """Leads its lowest card and answers with the cheapest combo that beats the
    pile — spends exactly enough to win, no more."""

    strategy = (
        "Leads its lowest card and answers with the cheapest combo that "
        "beats the pile — spends exactly enough to win, no more."
    )

    def make_decision(self, game_state):
        plays = [m for m in game_state["legal_moves"] if m]
        if plays:
            return min(plays, key=_combo_key)
        return []


class Greedy(Player):
    """Always slams down its biggest legal combo — burns 2s and bombs early."""

    strategy = (
        "Always slams down its biggest legal combo — burns its 2s and "
        "bombs early."
    )

    def make_decision(self, game_state):
        plays = [m for m in game_state["legal_moves"] if m]
        if plays:
            return max(plays, key=_combo_key)
        return []


class RandomBot(Player):
    """Plays a random legal combo (or passes at random)."""

    strategy = "Plays a random legal combo, or passes at random."

    def make_decision(self, game_state):
        return random.choice(game_state["legal_moves"])


# Order matters: _roster pads a short table with the first entries, and the
# single-game preview samples this list — so lead with a good spread of skill.
players = [
    Controller(),
    LowballShedder(),
    Beater(),
    Greedy(),
    RandomBot(),
]
