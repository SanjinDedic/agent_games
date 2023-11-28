from player_base import Player

class Testing_Player(Player):
    def make_decision(self, game_state):
        import random
        threshold = 18
        total_money = game_state['unbanked_money'][self.name] + game_state['banked_money'][self.name]
        unbanked = game_state['unbanked_money'][self.name]
        rank = self.my_rank(game_state)
        #bank if I have won
        if total_money >= 100:
            return 'bank'
        #continue if I am close to winning
        if total_money >= 96:
            return 'continue'
        #if another player has enough to win on their turn then bank!
        for player in game_state['unbanked_money']:
            if game_state['banked_money'][player] + game_state['unbanked_money'][player] >= 100:
                return 'bank'
        if rank > 4 and total_money > 60:
            threshold = 40
        if rank > 4 and total_money > 40:
            threshold = 35
        if unbanked >= threshold:
            if random.randint(0,10) >1:
                return 'bank'

        #if I am ranked last then continue
        return 'continue'
