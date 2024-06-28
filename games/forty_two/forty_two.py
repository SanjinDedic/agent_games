from games.base_game import BaseGame
import random

class FortyTwoGame(BaseGame):
    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)

    def play_round(self, player):
        hand = 0
        while True:
            game_state = self.get_game_state(player.name, hand)
            decision = player.make_decision(game_state)
            
            if decision == 'stand':
                break
            
            card = random.randint(1, 10)
            hand += card
            
            if hand > 42:
                break
            
            if self.verbose:
                print(f"{player.name} drew {card}, hand is now {hand}")
        
        return min(hand, 42)

    def get_game_state(self, player_name, current_hand):
        return {
            "player_name": player_name,
            "current_hand": current_hand,
            "scores": self.scores
        }

    def play_game(self):
        for player in self.players:
            hand = self.play_round(player)
            if hand <= 42:
                self.scores[player.name] += hand
            
            if self.verbose:
                print(f"{player.name} finished with {hand}")

        return {"points": self.scores}

def run_simulations(num_simulations, league):
    return BaseGame.run_simulations(num_simulations, FortyTwoGame, league)