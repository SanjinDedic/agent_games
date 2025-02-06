# Creating a New Game for agent_games

## Project Structure
When adding a new game to agent_games, follow this structure:

```
agent_games/
├── backend/
│   ├── games/
│   │   ├── your_game_name/
│   │   │   ├── __init__.py
│   │   │   ├── your_game_name.py  (main game logic)
│   │   │   ├── player.py          (player base class)
│   │   │   └── validation_players.py (default players)
│   │   └── game_factory.py        (register your game here)
│   └── tests/
        └── games/
            └── test_your_game_name.py
```

## Step 1: Create Required Files

### 1.1 Create the Game Directory and Files
Create a new directory under `backend/games/` with your game name and add these files:
- `__init__.py` (empty file)
- `your_game_name.py` (main game logic)
- `player.py` (player base class)
- `validation_players.py` (default/validation players)

### 1.2 Player Base Class (player.py)
Create the base Player class that all game players will inherit from:

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

### 1.3 Validation Players (validation_players.py)
Create default players for testing and validation:

```python
from backend.games.your_game_name.player import Player

class SimplePlayer(Player):
    def make_decision(self, game_state):
        # Implement basic strategy
        return decision

class SmartPlayer(Player):
    def make_decision(self, game_state):
        # Implement more complex strategy
        return decision

# Export list of players that will be auto-loaded
players = [SimplePlayer(), SmartPlayer()]
```

## Step 2: Implement Game Logic

### 2.1 Main Game Class
Create your game class inheriting from BaseGame in `your_game_name.py`:

```python
from backend.games.base_game import BaseGame

class YourGame(BaseGame):
    # Game Instructions - shown in UI when creating agent
    game_instructions = """
    <h1>Your Game Instructions</h1>
    <p>Explain rules, objectives, and how to implement an agent.</p>
    """

    # Starter code template for new agents
    starter_code = """
from games.your_game_name.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        '''
        game_state contains current game information
        return your decision based on the rules
        '''
        # Your code here
        return decision
    """

    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)
        # Initialize game-specific variables
        self.game_feedback = []
        self.player_feedback = {}

    def play_game(self, custom_rewards=None):
        """
        Main game loop - run a complete game
        Returns dict with game results
        """
        self.game_feedback = []  # Reset feedback
        # Implement game logic
        # Use self.add_feedback() for game progress
        # Collect player feedback
        return {
            "points": dict(self.scores),
            "score_aggregate": dict(self.scores),
            "table": {}  # Optional additional stats
        }

    def run_single_game_with_feedback(self, custom_rewards=None):
        """Run one game with detailed feedback"""
        self.verbose = True
        results = self.play_game(custom_rewards)
        return {
            "results": results,
            "feedback": self.game_feedback,
            "player_feedback": self.player_feedback
        }

    def run_simulations(self, num_simulations, league, custom_rewards=None):
        """Run multiple games for statistics"""
        total_points = {str(player.name): 0 for player in self.players}
        stats = {str(player.name): 0 for player in self.players}

        for _ in range(num_simulations):
            self.reset()
            results = self.play_game(custom_rewards)
            for player, points in results["points"].items():
                total_points[str(player)] += points
                # Update any additional statistics

        return {
            "total_points": total_points,
            "num_simulations": num_simulations,
            "table": {"stats": stats}
        }
```

### 2.2 Update Game Factory
Add your game to `game_factory.py`:

```python
from backend.games.your_game_name.your_game_name import YourGame

class GameFactory:
    @staticmethod
    def get_game_class(game_name):
        if game_name == "your_game_name":
            return YourGame
        # ... other games ...
        else:
            raise ValueError(f"Unknown game: {game_name}")
```

## Step 3: Implement Tests
Create test file in `backend/tests/games/test_your_game_name.py`:

```python
import pytest
from backend.games.your_game_name.your_game_name import YourGame
from backend.database.db_models import League
from datetime import datetime, timedelta

@pytest.fixture
def test_league():
    return League(
        name="test_league",
        created_date=datetime.now(),
        expiry_date=datetime.now() + timedelta(days=1),
        game="your_game_name"
    )

def test_game_initialization(test_league):
    game = YourGame(test_league)
    assert len(game.players) > 0  # Should have validation players
    assert isinstance(game.scores, dict)

def test_game_play(test_league):
    game = YourGame(test_league)
    results = game.play_game()
    assert "points" in results
    assert "score_aggregate" in results
    assert isinstance(results["points"], dict)

def test_game_feedback(test_league):
    game = YourGame(test_league, verbose=True)
    feedback_results = game.run_single_game_with_feedback()
    assert "feedback" in feedback_results
    assert "player_feedback" in feedback_results

def test_simulations(test_league):
    game = YourGame(test_league)
    results = game.run_simulations(10, test_league)
    assert "total_points" in results
    assert "num_simulations" in results
    assert results["num_simulations"] == 10
```

## Implementation Guidelines

### Feedback System
The game should provide detailed feedback in two ways:

1. Game Feedback (visible to all):
```python
self.add_feedback("## Round 1")
self.add_feedback("- Player A chose action X")
self.add_feedback("- Score update: A=10, B=5")
```

2. Player Feedback (private to each player):
```python
player.add_feedback(f"Considering options: {options}")
player.add_feedback(f"Selected strategy: {strategy}")
```

### Game State
Provide comprehensive game state to players:
```python
def get_game_state(self):
    return {
        "round_number": self.round_no,
        "scores": self.scores.copy(),
        "current_player": current_player.name,
        # Game-specific state information
    }
```

### Custom Rewards
Support custom reward structures:
```python
def play_game(self, custom_rewards=None):
    if custom_rewards:
        self.rewards = custom_rewards
    # Use self.rewards in scoring logic
```

## Example: AlphaGuess Implementation

Here's how you would implement the AlphaGuess game:

```python
# backend/games/alpha_guess/player.py
from abc import ABC, abstractmethod

class Player(ABC):
    def __init__(self):
        self.name = self.__class__.__name__
        self.feedback = []

    def add_feedback(self, message):
        self.feedback.append(message)

    @abstractmethod
    def make_decision(self, game_state):
        """Return a single lowercase letter guess"""
        pass

# backend/games/alpha_guess/validation_players.py
import random
import string
from backend.games.alpha_guess.player import Player

class RandomGuesser(Player):
    def make_decision(self, game_state):
        guess = random.choice(string.ascii_lowercase)
        self.add_feedback(f"Randomly chose letter: {guess}")
        return guess

class SmartGuesser(Player):
    def make_decision(self, game_state):
        # Use frequency analysis for better guessing
        common_letters = 'etaoinshrdlu'
        guess = random.choice(common_letters)
        self.add_feedback(f"Chose common letter: {guess}")
        return guess

players = [RandomGuesser(), SmartGuesser()]

# backend/games/alpha_guess/alpha_guess.py
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
import string

class CustomPlayer(Player):
    def make_decision(self, game_state):
        # game_state includes:
        # - round_number: current round
        # - scores: dict of current scores
        # - last_letter: the correct letter from last round
        
        # Your code here - return a lowercase letter
        guess = random.choice(string.ascii_lowercase)
        
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

    def play_game(self, custom_rewards=None):
        self.round_number = 0
        self.scores = {str(player.name): 0 for player in self.players}
        
        for round in range(self.rounds_per_game):
            self.round_number += 1
            self.current_letter = random.choice(string.ascii_lowercase)
            
            self.add_feedback(f"\n## Round {self.round_number}")
            self.add_feedback(f"Selected letter: {self.current_letter}")
            
            for player in self.players:
                game_state = {
                    "round_number": self.round_number,
                    "scores": dict(self.scores),
                    "last_letter": self.last_letter
                }
                
                guess = player.make_decision(game_state)
                self.add_feedback(f"\n### {player.name}'s turn")
                self.add_feedback(f"- Guessed: {guess}")
                
                if guess == self.current_letter:
                    self.scores[str(player.name)] += 1
                    self.add_feedback(f"- ✓ Correct! Score: {self.scores[str(player.name)]}")
                else:
                    self.add_feedback(f"- ✗ Incorrect. Score remains: {self.scores[str(player.name)]}")
                
                # Collect player feedback
                if player.feedback:
                    if str(player.name) not in self.player_feedback:
                        self.player_feedback[str(player.name)] = []
                    self.player_feedback[str(player.name)].extend(player.feedback)
                    player.feedback = []
            
            self.last_letter = self.current_letter
        
        return {
            "points": dict(self.scores),
            "score_aggregate": dict(self.scores),
            "table": {
                "rounds_played": self.round_number
            }
        }
```

## Testing Your Game
Run tests using pytest:
```bash
pytest backend/tests/games/test_your_game_name.py -v
```

The tests should verify:
- Game initialization
- Player management
- Game mechanics
- Scoring system
- Feedback system
- Simulation capabilities