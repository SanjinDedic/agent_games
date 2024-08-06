from games.base_game import BaseGame
import random

class TreasureHunt(BaseGame):
    starter_code = '''
from games.treasure_hunt.player import Player

class RandomPlayer(Player):
    def make_decision(self, game_state):
        return self.random_move(game_state)
'''

    game_instructions = '''
<h1>Treasure Hunt Game</h1>
<p>In this game, players navigate a grid to find hidden treasure.</p>
<p>Each player can move 'forward', 'left', or 'right'. The game ends when the treasure is found or all players have moved a certain number of times.</p>
<p>Players earn points based on their proximity to the treasure.</p>
'''

    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)
        self.grid_size = 5
        self.treasure_position = (random.randint(0, self.grid_size - 1), random.randint(0, self.grid_size - 1))
        self.player_positions = {player: (0, 0) for player in self.players}

    def get_game_state(self):
        return {
            "grid_size": self.grid_size,
            "player_positions": self.player_positions
        }
    
    def play_round(self):
        for player in self.players:
            move = player.make_decision(self.get_game_state())
            self.update_position(player, move)

    def play_game(self, custom_rewards=None):
        rounds = 10
        for _ in range(rounds):
            self.play_round()
            if self.treasure_found():
                break
        return self.calculate_results()

    def assign_points(self, scores, custom_rewards=None):
        points = {}
        for player, position in self.player_positions.items():
            distance = self.calculate_distance(position, self.treasure_position)
            points[player.name] = max(0, 10 - distance)  # Closer to treasure = more points
        return points

    def calculate_results(self):
        points = self.assign_points(self.player_positions)
        return {"points": points}

    def reset(self):
        super().reset()
        self.treasure_position = (random.randint(0, self.grid_size - 1), random.randint(0, self.grid_size - 1))
        self.player_positions = {player: (0, 0) for player in self.players}

    def update_position(self, player, move):
        x, y = self.player_positions[player]
        if move == "forward":
            y = min(y + 1, self.grid_size - 1)
        elif move == "left":
            x = max(x - 1, 0)
        elif move == "right":
            x = min(x + 1, self.grid_size - 1)
        self.player_positions[player] = (x, y)

    def treasure_found(self):
        return any(pos == self.treasure_position for pos in self.player_positions.values())

    def calculate_distance(self, position1, position2):
        return abs(position1[0] - position2[0]) + abs(position1[1] - position2[1])

def run_simulations(num_simulations, league, custom_rewards=None):
    return BaseGame.run_simulations(num_simulations, TreasureHunt, league, custom_rewards)
