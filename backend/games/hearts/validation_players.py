import random

from backend.games.hearts.player import Player


def _suit(card):
    return card[-1]


def _rank(card):
    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    return ranks.index(card[:-1]) + 2


def _danger(card):
    """How much this card wants to leave your hand (points, then rank)."""
    points = 13 if card == "QS" else (1 if _suit(card) == "H" else 0)
    return (points, _rank(card))


def _void_of_led(game_state):
    """True if you cannot follow the led suit (so anything is legal)."""
    trick = game_state["trick"]
    if not trick:
        return False
    led = _suit(trick[0]["card"])
    return not any(_suit(c) == led for c in game_state["hand"])


class RandomBot(Player):
    """Plays a random legal card; passes three random cards."""

    strategy = "Plays a random legal card and passes three random cards."

    def make_decision(self, game_state):
        if game_state["phase"] == "pass":
            return random.sample(game_state["hand"], 3)
        return random.choice(game_state["legal_moves"])


class LowballBot(Player):
    """Always plays its lowest legal card; passes its three highest cards."""

    strategy = (
        "Always plays its lowest legal card and passes its three highest "
        "cards — hopes low cards dodge the points."
    )

    def make_decision(self, game_state):
        if game_state["phase"] == "pass":
            return sorted(game_state["hand"], key=_rank, reverse=True)[:3]
        return min(game_state["legal_moves"], key=_rank)


class MoonShooter(Player):
    """Keeps its high cards (passes its lowest) and plays high to win tricks."""

    strategy = (
        "Keeps its high cards (passes the lowest) and plays high to win "
        "tricks — always flirting with shooting the moon."
    )

    def make_decision(self, game_state):
        if game_state["phase"] == "pass":
            return sorted(game_state["hand"], key=_rank)[:3]
        return max(game_state["legal_moves"], key=_rank)


class QueenDumper(Player):
    """Sheds high spades in the pass, slides the Queen the moment it is void."""

    strategy = (
        "Passes away its high spades, then dumps the Queen of Spades on "
        "someone the moment it can't follow suit."
    )

    def make_decision(self, game_state):
        hand = game_state["hand"]
        if game_state["phase"] == "pass":
            spades = [c for c in hand if c in ("QS", "KS", "AS")]
            rest = sorted(
                (c for c in hand if c not in spades), key=_danger, reverse=True
            )
            return (spades + rest)[:3]
        legal = game_state["legal_moves"]
        if _void_of_led(game_state) and "QS" in legal:
            return "QS"
        if _void_of_led(game_state):
            return sorted(legal, key=_danger, reverse=True)[0]
        return min(legal, key=_rank)


class HeartAvoider(Player):
    """Passes away hearts and the Queen; refuses to take hearts when it can."""

    strategy = (
        "Passes away hearts and the Queen, and refuses to play hearts "
        "whenever it has any other legal choice."
    )

    def make_decision(self, game_state):
        hand = game_state["hand"]
        if game_state["phase"] == "pass":
            return sorted(hand, key=_danger, reverse=True)[:3]
        legal = game_state["legal_moves"]
        if _void_of_led(game_state):
            return sorted(legal, key=_danger, reverse=True)[0]
        non_hearts = [c for c in legal if _suit(c) != "H"]
        return min(non_hearts or legal, key=_rank)


class TrickDucker(Player):
    """Tries to lose every trick: follows with the highest card that still
    stays under the current winner; leads low, dumps danger when void."""

    strategy = (
        "Tries to lose every trick: follows with the highest card that still "
        "stays under the current winner, leads low, and dumps dangerous cards "
        "when it can't follow suit."
    )

    def make_decision(self, game_state):
        hand = game_state["hand"]
        if game_state["phase"] == "pass":
            return sorted(hand, key=_danger, reverse=True)[:3]
        legal = game_state["legal_moves"]
        trick = game_state["trick"]
        if not trick:
            return min(legal, key=_rank)  # lead low
        led = _suit(trick[0]["card"])
        top = max(
            (_rank(p["card"]) for p in trick if _suit(p["card"]) == led), default=0
        )
        under = [c for c in legal if _suit(c) == led and _rank(c) < top]
        if under:
            return max(under, key=_rank)  # duck as high as safely possible
        if _void_of_led(game_state):
            return sorted(legal, key=_danger, reverse=True)[0]  # can't follow: dump
        return min(legal, key=_rank)  # forced to win: lose as little as possible


class VoidMaker(Player):
    """Passes three cards from its shortest suit to go void fast, then dumps
    its most dangerous card whenever it cannot follow; otherwise plays low."""

    strategy = (
        "Passes from its shortest suit to go void fast, then dumps its most "
        "dangerous card whenever it can't follow suit; otherwise plays low."
    )

    def make_decision(self, game_state):
        hand = game_state["hand"]
        if game_state["phase"] == "pass":
            counts = {}
            for c in hand:
                counts[_suit(c)] = counts.get(_suit(c), 0) + 1
            return sorted(hand, key=lambda c: (counts[_suit(c)], _rank(c)))[:3]
        legal = game_state["legal_moves"]
        if _void_of_led(game_state):
            return sorted(legal, key=_danger, reverse=True)[0]
        return min(legal, key=_rank)


class Cautious(Player):
    """Passes its most dangerous cards, plays low, dumps danger when void."""

    strategy = (
        "Passes its most dangerous cards, plays low whenever it must follow, "
        "and sheds danger cards when it can't."
    )

    def make_decision(self, game_state):
        hand = game_state["hand"]
        if game_state["phase"] == "pass":
            return sorted(hand, key=_danger, reverse=True)[:3]
        legal = game_state["legal_moves"]
        if _void_of_led(game_state):
            return sorted(legal, key=_danger, reverse=True)[0]
        return min(legal, key=_rank)


players = [
    RandomBot(),
    LowballBot(),
    MoonShooter(),
    QueenDumper(),
    HeartAvoider(),
    TrickDucker(),
    VoidMaker(),
    Cautious(),
]
