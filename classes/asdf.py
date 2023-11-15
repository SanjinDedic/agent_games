from player_base import Player

class New2_Player(Player):
    def make_decision(self, game_state):
        print(self.my_rank(game_state))
        print(game_state)
        import random
        if game_state['unbanked_money'][self.name] >= 11:
            if random.randint(0,10) > 1:
                return 'bank'
        return 'continue'
