from abc import ABC, abstractmethod
import random
import json

class Player(ABC):
    def __init__(self, name, password):
        self.name = name
        self.password = password
        self.banked_money = 0
        self.unbanked_money = 0
        self.has_banked_this_turn = False  # Track banking status within a turn
        self.color = 'white'

    def reset_unbanked_money(self):
        self.unbanked_money = 0

    def bank_money(self):
        self.banked_money += self.unbanked_money
        self.reset_unbanked_money()

    def reset_turn(self):
        self.has_banked_this_turn = False  # Reset banking status at the start of each turn

    def my_rank(self, game_state):
        # Extract the points_aggregate dictionary
        points_aggregate = dict()
        for player in game_state['banked_money']:
            points_aggregate[player] = game_state['banked_money'][player]+game_state['unbanked_money'][player]
        # Sort the dictionary by its values in descending order

        sorted_players = sorted(points_aggregate, key=points_aggregate.get, reverse=True)
        try:
            rank = sorted_players.index(self.name) + 1
            return rank
        except ValueError:
            return 0

    @abstractmethod
    def make_decision(self, game_state):
        pass