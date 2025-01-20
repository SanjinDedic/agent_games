from games.greedy_pig.player import Player

class Bank5(Player):
    """Player that banks after accumulating more than 5 points"""
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 5:
            return 'bank'
        return 'continue'

class Bank15(Player):
    """Player that banks after accumulating more than 15 points"""
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 15:
            return 'bank'
        return 'continue'

class BankRoll3(Player):
    """Player that banks after 3 rolls"""
    def make_decision(self, game_state):
        if game_state["roll_no"] == 3:
            return 'bank'
        return 'continue'

class BankRoll4(Player):
    """Player that banks after 4 rolls"""
    def make_decision(self, game_state):
        if game_state["roll_no"] == 4:
            return 'bank'
        return 'continue'
    
class StopAt21(Player):
    """Player that banks after accumulating more than 21 points"""
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 21:
            return 'bank'
        return 'continue'

players = [
        Bank5(),
        Bank15(),
        BankRoll3(),
        BankRoll4(),
        StopAt21()
    ]