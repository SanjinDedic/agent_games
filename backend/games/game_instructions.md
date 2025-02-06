# Creating a New Game for agent_games

## Required Files
Create these files in your game directory (e.g., `backend/games/alpha_guess/`):

1. `__init__.py` (empty file)
2. `player.py` 
3. `alpha_guess.py` 
4. `validation_players.py`

## 1. Base Player Class (player.py)
```python
from abc import ABC, abstractmethod

class Player(ABC):
    def __init__(self):
        self.name = self.__class__.__name__
        self.feedback = []

    def add_feedback(self, message):
        self.feedback.append(message)

    @abstractmethod
    def make_decision(self, game_state):
        pass
```

## 2. Validation Players (validation_players.py)
```python
import random
import string
from backend.games.alpha_guess.player import Player

class RandomGuesser(Player):
    def make_decision(self, game_state):
        guess = random.choice(string.ascii_lowercase)
        self.add_feedback(f"Random guess: {guess}")
        return guess

class SmartGuesser(Player):
    def make_decision(self, game_state):
        common_letters = 'etaoinshrdlu'
        guess = random.choice(common_letters)
        self.add_feedback(f"Smart guess: {guess}")
        return guess

players = [RandomGuesser(), SmartGuesser()]
```

## 3. Main Game Class (alpha_guess.py)
```python
import random
import string
from backend.games.base_game import BaseGame

class AlphaGuessGame(BaseGame):
    game_instructions = """
    <h1>Alpha Guess Game Instructions</h1>
    <p>Try to guess the randomly chosen letter! Each correct guess scores a point.</p>
    <h2>Rules:</h2>
    <ul>
        <li>Each round, a random lowercase letter is chosen</li>
        <li>Players submit their guesses</li>
        <li>Correct guesses score 1 point</li>
        <li>Game continues for specified number of rounds</li>
    </ul>
    """

    starter_code = """
from games.alpha_guess.player import Player
import random

class CustomPlayer(Player):
    def make_decision(self, game_state):
        guess = random.choice(['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z'])
        
        # Add custom feedback (will appear in game output)
        self.add_feedback(f"My guess: {guess}")
        
        return guess
"""

    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)
        self.round_number = 0
        self.current_letter = None
        self.last_letter = None
        self.rounds_per_game = 10
        self.game_feedback = {"rounds": []}

    def play_game(self, custom_rewards=None):
        self.round_number = 0
        self.scores = {str(player.name): 0 for player in self.players}
        
        # Clear previous feedback
        self.game_feedback = {"rounds": []}
        self.player_feedback = {}
        
        for round in range(self.rounds_per_game):
            self.round_number += 1
            self.current_letter = random.choice(string.ascii_lowercase)
            
            round_data = {
                "round_number": self.round_number,
                "target_letter": self.current_letter,
                "player_actions": []
            }
            
            for player in self.players:
                game_state = {
                    "round_number": self.round_number,
                    "scores": dict(self.scores),
                    "last_letter": self.last_letter
                }
                
                guess = player.make_decision(game_state)
                correct = guess == self.current_letter
                
                if correct:
                    self.scores[str(player.name)] += 1
                
                player_action = {
                    "player": str(player.name),
                    "guess": guess,
                    "correct": correct,
                    "score": self.scores[str(player.name)]
                }
                round_data["player_actions"].append(player_action)
                
                # Collect player feedback
                if player.feedback:
                    if str(player.name) not in self.player_feedback:
                        self.player_feedback[str(player.name)] = []
                    self.player_feedback[str(player.name)].extend(player.feedback)
                    player.feedback = []
            
            self.game_feedback["rounds"].append(round_data)
            self.last_letter = self.current_letter
        
        # Add final scores to feedback
        self.game_feedback["final_scores"] = dict(self.scores)
        
        return {
            "points": dict(self.scores),
            "score_aggregate": dict(self.scores),
            "table": {
                "rounds_played": self.round_number
            }
        }

    def run_simulations(self, num_simulations, league, custom_rewards=None):
        """Run multiple simulations"""
        total_points = {str(player.name): 0 for player in self.players}
        correct_guesses = {str(player.name): 0 for player in self.players}
        total_guesses = {str(player.name): 0 for player in self.players}

        for _ in range(num_simulations):
            self.reset()
            results = self.play_game(custom_rewards)
            
            for player, points in results["points"].items():
                total_points[str(player)] += points
                correct_guesses[str(player)] += points  # Each point represents a correct guess
                total_guesses[str(player)] += self.rounds_per_game  # Total guesses per game

        return {
            "total_points": total_points,
            "num_simulations": num_simulations,
            "table": {
                "correct_guesses": correct_guesses,
                "total_guesses": total_guesses
            }
        }
```

## 4. Update Game Factory
Add to `game_factory.py`:
```python
from backend.games.alpha_guess.alpha_guess import AlphaGuessGame

class GameFactory:
    @staticmethod
    def get_game_class(game_name):
        if game_name == "alpha_guess":
            return AlphaGuessGame
        # ... other games ...
        else:
            raise ValueError(f"Unknown game: {game_name}")
```

## 5. Docker Container Rebuild
After adding files:
1. Stop containers:
```bash
python -c "from backend.docker_utils.containers import stop_containers; stop_containers()"
```

2. Restart API server (containers will rebuild):
```bash
uvicorn backend.api:app --reload
```

## Notes
- Game feedback uses dictionary format for structured data
- Player feedback can be strings or dictionaries
- Always use str(player.name) for consistency
- Reset feedback at start of each game