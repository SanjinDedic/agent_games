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


players = [Bank5(), Bank15(), BankRoll3(), BankRoll4(), StopAt21()]
