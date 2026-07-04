from backend.games.hearts.player import Player


def _suit(card):
    return card[-1]


def _rank(card):
    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    return ranks.index(card[:-1]) + 2


def _danger(card):
    """How much this card wants to leave your hand."""
    points = 13 if card == "QS" else (1 if _suit(card) == "H" else 0)
    return (points, _rank(card))


class Cautious(Player):
    """Passes its most dangerous cards, plays low, dumps danger when void."""

    def make_decision(self, game_state):
        hand = game_state["hand"]
        if game_state["phase"] == "pass":
            return sorted(hand, key=_danger, reverse=True)[:3]
        legal = game_state["legal_moves"]
        trick = game_state["trick"]
        if trick and not any(_suit(c) == _suit(trick[0]["card"]) for c in hand):
            return sorted(legal, key=_danger, reverse=True)[0]
        return min(legal, key=_rank)


class QueenDumper(Player):
    """Sheds high spades in the pass, slides the Queen the moment it is void."""

    def make_decision(self, game_state):
        hand = game_state["hand"]
        if game_state["phase"] == "pass":
            spades = [c for c in hand if c in ("QS", "KS", "AS")]
            rest = sorted(
                (c for c in hand if c not in spades), key=_danger, reverse=True
            )
            return (spades + rest)[:3]
        legal = game_state["legal_moves"]
        trick = game_state["trick"]
        led_void = trick and not any(
            _suit(c) == _suit(trick[0]["card"]) for c in hand
        )
        if led_void and "QS" in legal:
            return "QS"
        if led_void:
            return sorted(legal, key=_danger, reverse=True)[0]
        return min(legal, key=_rank)


class MoonChaser(Player):
    """Keeps its high cards and tries to win every trick."""

    def make_decision(self, game_state):
        if game_state["phase"] == "pass":
            return sorted(game_state["hand"], key=_rank)[:3]
        return max(game_state["legal_moves"], key=_rank)


players = [Cautious(), QueenDumper(), MoonChaser()]
