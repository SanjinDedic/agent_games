from player_base import Player

class Testing_Player(Player):
    def make_decision(self, game_state):
        import random
        threshold = 20
        #bank if I have won
        total_money = game_state['unbanked_money'][self.name] + game_state['banked_money'][self.name]

        if total_money >= 100:
            return 'bank'
        #continue if I am close to winning
        if total_money >= 96:
            return 'continue'
        if self.my_rank(game_state) > 5 and total_money > 80:
            return 'continue'
        if game_state['unbanked_money'][self.name] >= threshold:
            if random.randint(0,10) >1:
                return 'bank'
