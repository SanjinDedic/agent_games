import random
import time
import os
import importlib.util
from models_db import League

class Game:
    def __init__(self, league, verbose=False):
        self.verbose = verbose
        self.players = self.get_all_player_classes_from_folder(league.folder)
        self.active_players = list(self.players)
        self.players_banked_this_round = []
        self.round_no = 0
        self.roll_no = 0
        self.game_over = False

    def roll_dice(self):
        return random.randint(1, 6)

    def get_game_state(self):
        return {
            "round_no": self.round_no,
            "roll_no": self.roll_no,
            "players_banked_this_round": self.players_banked_this_round,
            "banked_money": {player.name: player.banked_money for player in self.players},
            "unbanked_money": {player.name: player.unbanked_money for player in self.players},
        }

    def play_round(self):
        self.players_banked_this_round = []
        self.round_no += 1
        self.roll_no = 0

        while True:
            self.roll_no += 1
            roll = self.roll_dice()
            if self.verbose:
                print(f' Dice says {roll}')

            if roll == 1:
                if self.verbose:
                    print("  Oops! Rolled a 1. All players lose their unbanked money.")
                for player in self.active_players:
                    if player.unbanked_money > 0 and self.verbose:
                        print(f"    * {player.name} loses ${player.unbanked_money} of unbanked money.")
                    player.reset_unbanked_money()
                break

            for player in self.active_players.copy():
                if not player.has_banked_this_turn:
                    player.unbanked_money += roll
                    if self.verbose:
                        print(f"{player.name} now has ${player.unbanked_money} unbanked.")
                    decision = player.make_decision(self.get_game_state())
                    if decision == 'bank':
                        if self.verbose:
                            print(f"    * {player.name} decides to bank ${player.unbanked_money}.")
                        player.bank_money()
                        player.has_banked_this_turn = True
                        self.players_banked_this_round.append(player.name)
                        self.active_players.remove(player)

            for player in self.active_players:
                if player.banked_money + player.unbanked_money >= 100:
                    self.game_over = True
                    return

        for player in self.players:
            player.reset_turn()

    def play_game(self):
        random.shuffle(self.players)
        while self.game_over == False:
            self.active_players = list(self.players)
            if self.verbose:
                print('\nSTART ROUND #' + str(self.round_no))
            winner = self.play_round()
            if winner and self.verbose:
                print(f"\nGame Over: {winner} has won the game!")
                break
            if self.verbose:
                print('  END OF ROUND #' + str(self.round_no))
                print(self.get_game_state())
                for player in self.players:
                    print('  ' + player.name + ': $' + str(player.banked_money))

        game_state = self.get_game_state()
        results = self.assign_points(game_state)
        return results

    def assign_points(self, game_state):
        score_aggregate = dict()
        for player in game_state['banked_money']:
            score_aggregate[player] = game_state['banked_money'][player] + game_state['unbanked_money'][player]
        
        sorted_players = sorted(score_aggregate.items(), key=lambda x: x[1], reverse=True)
        
        points = dict()
        points_on_offer = len(score_aggregate)
        tie=True
        if self.verbose:
            print("sorted_players")
            print(sorted_players)
        for player in sorted_players:
            points[player[0]] = points_on_offer
            if self.verbose:
                print(player, points_on_offer)  
            points_on_offer -= 1
        while tie:
            tie = False
            for i in range(1, len(sorted_players)):
                if sorted_players[i][1] == sorted_players[i-1][1] and points[sorted_players[i][0]] < points[sorted_players[i-1][0]]:
                    points[sorted_players[i][0]] += 1
                    tie = True

        return {"points": points, "score_aggregate": score_aggregate}

    def get_all_player_classes_from_folder(self, folder_name):
        #folder_name is relative path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        league_directory = os.path.join(current_dir, folder_name)

        if self.verbose:
            print("Current directory:", current_dir)
            print("League:", league_directory)

        if not os.path.exists(league_directory):
            if self.verbose:
                print(f"The folder '{league_directory}' does not exist.")
            return []

        if self.verbose:
            print("Files and directories in the league folder:")
        player_classes = []
        for item in os.listdir(league_directory):
            if self.verbose:
                print(item)
            if item.endswith(".py"):
                if self.verbose:
                    print(f"Found a Python file: {item}")
                module_name = item[:-3]
                module_path = os.path.join(league_directory, item)
                if self.verbose:
                    print(f"Module name: {module_name}")
                    print(f"Module path: {module_path}")

                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if self.verbose:
                    print(f"Loaded module: {module}")
                    print(f"Module attributes: {dir(module)}")

                if hasattr(module, "CustomPlayer"):
                    player_class = getattr(module, "CustomPlayer")
                    if self.verbose:
                        print(f"Found CustomPlayer class: {player_class}")
                    player = player_class()
                    player.name = module_name  # Use the module name as is
                    if self.verbose:
                        print(f"Created player instance: {player}")
                    player_classes.append(player)
                elif self.verbose:
                    print(f"CustomPlayer class not found in module: {module_name}")

        if self.verbose:
            print(f"Found {len(player_classes)} player classes.")
        return player_classes
    
    def reset(self):
        self.active_players = list(self.players)
        self.players_banked_this_round = []
        self.round_no = 0
        self.roll_no = 0
        self.game_over = False
        
        for player in self.players:
            player.banked_money = 0
            player.unbanked_money = 0
            player.has_banked_this_turn = False
