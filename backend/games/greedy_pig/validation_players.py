from backend.games.greedy_pig.player import Player


class Bank5(Player):
    """Player that banks after accumulating more than 5 points"""

    strategy = (
        "Banks as soon as its unbanked money goes over 5 points — "
        "very cautious, takes small but safe gains every turn."
    )

    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 5:
            return "bank"
        return "continue"


class Bank15(Player):
    """Player that banks after accumulating more than 15 points"""

    strategy = (
        "Banks once its unbanked money goes over 15 points — "
        "a middle ground between safety and greed."
    )

    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 15:
            return "bank"
        return "continue"


class BankRoll3(Player):
    """Player that banks after 3 rolls"""

    strategy = (
        "Banks on the 3rd roll of every turn, regardless of how much "
        "money is at stake."
    )

    def make_decision(self, game_state):
        if game_state["roll_no"] == 3:
            return "bank"
        return "continue"


class BankRoll4(Player):
    """Player that banks after 4 rolls"""

    strategy = (
        "Banks on the 4th roll of every turn — rides the risk one roll "
        "longer than BankRoll3."
    )

    def make_decision(self, game_state):
        if game_state["roll_no"] == 4:
            return "bank"
        return "continue"


class StopAt21(Player):
    """Player that banks after accumulating more than 21 points"""

    strategy = (
        "Banks only once its unbanked money goes over 21 points — "
        "greedy, chases big turns and risks losing them."
    )

    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 21:
            return "bank"
        return "continue"


class StopAt20Win100(Player):
    """Player that banks over 20 points, or immediately when banking wins the game"""

    strategy = (
        "Banks once its unbanked money goes over 20 points, but banks "
        "immediately whenever banked + unbanked reaches 100 — never risks "
        "rolling away a winning total."
    )

    def make_decision(self, game_state):
        my_unbanked = game_state["unbanked_money"][self.name]
        my_banked = game_state["banked_money"][self.name]
        if my_unbanked > 20 or my_banked + my_unbanked >= 100:
            return "bank"
        return "continue"


class AdaptiveRankStop(Player):
    """Player that banks over 15 points when ranked 1st, over 25 otherwise"""

    strategy = (
        "Plays it safe in the lead and greedy when behind — banks once "
        "unbanked money goes over 15 points while ranked 1st, but holds "
        "out past 25 points when not in 1st place."
    )

    def make_decision(self, game_state):
        threshold = 15 if self.my_rank(game_state) == 1 else 25
        if game_state["unbanked_money"][self.name] > threshold:
            return "bank"
        return "continue"


players = [
    Bank5(),
    Bank15(),
    BankRoll3(),
    BankRoll4(),
    StopAt21(),
    StopAt20Win100(),
    AdaptiveRankStop(),
]
