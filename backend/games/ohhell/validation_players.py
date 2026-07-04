import random

from backend.games.ohhell.player import Player

RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]


def _suit(card):
    return card[-1]


def _rank(card):
    return RANKS.index(card[:-1]) + 2  # 2..14 (Ace high)


def _nudge_bid(bid, cards, forbidden):
    """Clamp bid to [0, cards] and step off the forbidden value if needed."""
    bid = max(0, min(cards, bid))
    if forbidden is not None and bid == forbidden:
        if bid + 1 <= cards:
            bid += 1
        elif bid - 1 >= 0:
            bid -= 1
    return bid


def _wins_against_table(card, trick, trump):
    """Would `card`, played now, be the highest on the table so far?"""
    plays = [p["card"] for p in trick] + [card]
    led = _suit(plays[0])
    trumps = [c for c in plays if _suit(c) == trump]
    pool = trumps if trumps else [c for c in plays if _suit(c) == led]
    return max(pool, key=_rank) == card


class RandomBot(Player):
    """Bids at random and plays a random legal card."""

    def make_decision(self, game_state):
        if game_state["phase"] == "bid":
            cards = game_state["cards_this_round"]
            forbidden = game_state["forbidden_bid"]
            choices = [b for b in range(cards + 1) if b != forbidden]
            return random.choice(choices)
        return random.choice(game_state["legal_moves"])


class ZeroBidder(Player):
    """Always bids 0 and always plays its lowest card to shed tricks."""

    def make_decision(self, game_state):
        if game_state["phase"] == "bid":
            return _nudge_bid(0, game_state["cards_this_round"], game_state["forbidden_bid"])
        return min(game_state["legal_moves"], key=_rank)


class GreedyBidder(Player):
    """Bids high and always plays high — tries to win everything."""

    def make_decision(self, game_state):
        if game_state["phase"] == "bid":
            cards = game_state["cards_this_round"]
            return _nudge_bid(cards, cards, game_state["forbidden_bid"])
        return max(game_state["legal_moves"], key=_rank)


class AceCounter(Player):
    """Bids one per off-suit ace plus high trump; plays high, then ducks."""

    def make_decision(self, game_state):
        hand = game_state["hand"]
        trump = game_state["trump"]
        if game_state["phase"] == "bid":
            cards = game_state["cards_this_round"]
            est = sum(1 for c in hand if _rank(c) == 14 and _suit(c) != trump)
            est += sum(1 for c in hand if _suit(c) == trump and _rank(c) >= 12)
            return _nudge_bid(est, cards, game_state["forbidden_bid"])
        return self._play(game_state)

    def _play(self, game_state):
        legal = game_state["legal_moves"]
        need = game_state["bids"][self.name] - game_state["tricks_won"][self.name]
        if need > 0:
            return max(legal, key=_rank)  # still want tricks: play high
        return min(legal, key=_rank)  # made the bid: duck low


class Estimator(Player):
    """Estimates tricks from high cards and trump length, then plays to hit the
    bid exactly — wins as cheaply as possible while short, ducks once satisfied."""

    def make_decision(self, game_state):
        if game_state["phase"] == "bid":
            return self._bid(game_state)
        return self._play(game_state)

    def _bid(self, game_state):
        hand = game_state["hand"]
        trump = game_state["trump"]
        cards = game_state["cards_this_round"]
        off_aces = sum(1 for c in hand if _rank(c) == 14 and _suit(c) != trump)
        high_trumps = sum(1 for c in hand if _suit(c) == trump and _rank(c) >= 12)
        low_trumps = sum(1 for c in hand if _suit(c) == trump and _rank(c) < 12)
        est = off_aces + high_trumps + 0.4 * low_trumps
        return _nudge_bid(round(est), cards, game_state["forbidden_bid"])

    def _play(self, game_state):
        legal = game_state["legal_moves"]
        trump = game_state["trump"]
        trick = game_state["trick"]
        need = game_state["bids"][self.name] - game_state["tricks_won"][self.name]

        if not trick:  # leading
            if need > 0:
                return max(legal, key=_rank)  # lead strength to grab a trick
            return min(legal, key=_rank)  # want no more: lead low

        winners = [c for c in legal if _wins_against_table(c, trick, trump)]
        losers = [c for c in legal if c not in winners]
        if need > 0 and winners:
            return min(winners, key=_rank)  # win, but spend the cheapest winner
        if losers:
            return max(losers, key=_rank)  # duck: shed the highest safe loser
        return min(legal, key=_rank)  # forced to win: minimise the damage


# Order matters: _roster pads a short table with the first entries, and the
# single-game preview samples this list — so lead with a good spread of skill.
players = [
    Estimator(),
    AceCounter(),
    ZeroBidder(),
    RandomBot(),
    GreedyBidder(),
]
