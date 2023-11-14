import random
import os
import time
from player_base import Player

class Dice:
    def roll(self):
        return random.randint(1, 6)

class Game:
    def __init__(self, player_class):
        # Create player instance from the provided class
        self.player = player_class
        self.active_player = self.player  # Only one player, so this is straightforward
        self.dice = Dice()

    def get_game_state(self):
        return {
            "banked_money": {self.player.name: self.player.banked_money},
            "unbanked_money": {self.player.name: self.player.unbanked_money}
        }

    def play_round(self):
        roll = self.dice.roll()
        if roll == 1:
            self.active_player.reset_unbanked_money()
            return
        self.active_player.unbanked_money += roll
        decision = self.active_player.make_decision(self.get_game_state())

        if decision not in ['bank','continue']:
            return "Not Validated"
        
        if decision == 'bank':
            self.active_player.bank_money()
            

    def play_game(self):
        while self.player.banked_money < 100:
            result = self.play_round()
            if isinstance(result,str):
                return "Not Validated"
        return self.get_game_state()


    
def run_single_simulation(PlayerClass, team_name, password):
    if issubclass(PlayerClass, Player) and PlayerClass is not Player:
        player_class = PlayerClass(team_name, password)
        if not player_class:
            return "Not Validated"
    
        game = Game(player_class)
        game_result = game.play_game()
        if game_result=='Not Validated':
            return "Not Validated"
        elif game_result:
            return "Validated"
    else:
        return "Invalid player class. Must extend the base Player class."

