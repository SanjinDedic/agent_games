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
            'round_no': 9, 'roll_no': 0, 'players_banked_this_round': ["a"],
            "banked_money": {self.player.name: self.player.banked_money,
                            "a":0,
                            "b":0,
                            "c":0,
                            "d":0,
                            "e":0,
                            "f":0,
                            "g":0,
                            "h":0,
                            "i":0,
                            "j":0,
                            "k":0,
                            "l":0,
                            "m":0,
                            "n":0},
            "unbanked_money": {self.player.name: self.player.unbanked_money,
                            "a":0,
                            "b":0,
                            "c":0,
                            "d":0,
                            "e":0,
                            "f":0,
                            "g":0,
                            "h":0,
                            "i":10,
                            "j":11,
                            "k":12,
                            "l":13,
                            "m":14,
                            "n":15}
        }


    def play_round(self):
        try:
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
        except Exception as e:
            return 'Not Validated'
            

    def play_game(self):
        round_counter = 0
        max_rounds = 1000
        start_time = time.time()
        while self.player.banked_money < 100:
            round_counter += 1
            result = self.play_round()
            if round_counter > max_rounds:
                return "Not Validated: Stuck in endless loop"
            if isinstance(result,str) or result=='Not Validated':
                return "Not Validated"
            if time.time() - start_time > 5:
                return "Not Validated: Stuck in endless loop"
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
        elif game_result == "Not Validated: Stuck in endless loop":
            return "Not Validated: Stuck in endless loop"
        elif game_result:
            return "Validated"
    else:
        return "Invalid player class. Must extend the base Player class."

