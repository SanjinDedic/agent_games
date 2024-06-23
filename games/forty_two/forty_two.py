import random
import os
import importlib.util

class Game:
    def __init__(self, league, verbose=False):
        self.verbose = verbose
        self.players = self.get_all_player_classes_from_folder(league.folder)
        self.scores = {player.name: 0 for player in self.players}

    def get_all_player_classes_from_folder(self, folder_name):
        players = []
        current_dir = os.path.dirname(os.path.abspath(__file__))
        league_directory = os.path.join(current_dir, '..', '..', folder_name)

        if not os.path.exists(league_directory):
            print(f"The folder '{league_directory}' does not exist.")
            return players

        for item in os.listdir(league_directory):
            if item.endswith(".py"):
                module_name = item[:-3]
                module_path = os.path.join(league_directory, item)

                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if hasattr(module, "CustomPlayer"):
                    player_class = getattr(module, "CustomPlayer")
                    player = player_class()
                    player.name = module_name
                    players.append(player)

        return players

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
        
        return hand

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

    def reset(self):
        self.scores = {player.name: 0 for player in self.players}

def run_simulations(num_simulations, league):
    game = Game(league)
    total_points = {player.name: 0 for player in game.players}
    total_wins = {player.name: 0 for player in game.players}

    for _ in range(num_simulations):
        game.reset()
        results = game.play_game()
        
        for player, points in results["points"].items():
            total_points[player] += points
        
        winner = max(results["points"], key=results["points"].get)
        total_wins[winner] += 1

    return {
        "total_points": total_points,
        "total_wins": total_wins,
        "num_simulations": num_simulations
    }