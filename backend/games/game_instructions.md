Certainly! Here's an expanded version of Part 1 with a folder map:

# Creating a New Game for agent_games

## Part 1: General Instructions

1. **Create the Game Directory**
   - Create a new directory in the `games` folder, named after your game (use snake_case).
   - Have your folder structure look like this:

```
agent_games/
├── games/
│   ├── your_game_name/
│   │   ├── your_game_name.py
│   │   ├── player.py
│   │   └── leagues/
│   │       └── test_league/
│   │           └── example_bot.py
│   └── game_factory.py
├── tests/
│   └── test_your_game_name.py
└── README.md
```

2. **Implement the Game Class**
   - Create a Python file named after your game (e.g., `your_game_name.py`).
   - Implement your game class, inheriting from `BaseGame`. Include methods for game logic and state management.

3. **Create the Player Class**
   - Create a `player.py` file in your game directory.
   - Define a base `Player` class with a `make_decision` method that subclasses will implement.

4. **Update the Game Factory**
   - Add your game to the `game_factory.py` file in the `games` directory.
   - This allows the framework to instantiate your game when requested.

5. **Add Test League Bots**
   - Create example bots in the `test_league` folder.
   - These bots will be used for testing and as opponents for submitted player code.

6. **Create Unit Tests**
   - Add a test file in the `tests` directory (e.g., `test_your_game_name.py`).
   - Write tests to verify your game's logic, scoring, and integration with the framework.

7. **Update Documentation**
   - Add information about your new game to the project README.
   - Include any specific instructions or rules for your game.


## Part 2: Example - Adding AlphaGuess Game

Let's create a simple letter guessing game called "AlphaGuess".

1. **Create the Game Directory**

```
agent_games/
└── games/
    └── alpha_guess/
        ├── alpha_guess.py
        ├── player.py
        └── leagues/
            └── test_league/
```

2. **Implement the Game Class (alpha_guess.py)**

```python
from games.base_game import BaseGame
import random
import string

class AlphaGuessGame(BaseGame):
    starter_code = '''
from games.alpha_guess.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return random.choice(string.ascii_lowercase)
'''

    game_instructions = '''
<h1>AlphaGuess Game Instructions</h1>
<p>Guess the randomly selected letter (a-z). Correct guesses earn 1 point.</p>
'''

    def __init__(self, league):
        super().__init__(league)
        self.correct_letter = None

    def play_round(self):
        self.correct_letter = random.choice(string.ascii_lowercase)
        for player in self.players:
            if player.make_decision(self.get_game_state()) == self.correct_letter:
                self.scores[player.name] = 1
            else:
                self.scores[player.name] = 0

    def get_game_state(self):
        return {"correct_letter": self.correct_letter}

    def play_game(self, custom_rewards=None):
        self.play_round()
        return self.assign_points(self.scores, custom_rewards)

    def assign_points(self, scores, custom_rewards=None):
        return {"points": scores, "score_aggregate": scores}

def run_simulations(num_simulations, league, custom_rewards=None):
    return BaseGame.run_simulations(num_simulations, league, custom_rewards)
```

3. **Create the Player Class (player.py)**

```python
from abc import ABC, abstractmethod

class Player(ABC):
    @abstractmethod
    def make_decision(self, game_state):
        pass
```

4. **Update the Game Factory (game_factory.py)**

```python
from games.alpha_guess.alpha_guess import AlphaGuessGame

class GameFactory:
    @staticmethod
    def get_game_class(game_name):
        if game_name == "alpha_guess":
            return AlphaGuessGame
        else:
            raise ValueError(f"Unknown game: {game_name}")
```

5. **Add Test League Bot**

Create `games/alpha_guess/leagues/test_league/random_bot.py`:

```python
from games.alpha_guess.player import Player
import random
import string

class CustomPlayer(Player):
    def make_decision(self, game_state):
        return random.choice(string.ascii_lowercase)
```

6. **Testing**

Create `tests/test_alpha_guess.py`:

```python
import pytest
from games.alpha_guess.alpha_guess import AlphaGuessGame
from models_db import League

@pytest.fixture
def test_league():
    return League(name="test_league", folder="leagues/test_league", game="alpha_guess")

def test_play_game(test_league):
    game = AlphaGuessGame(test_league)
    results = game.play_game()
    assert "points" in results
    assert "score_aggregate" in results
    assert all(score >= 0 for score in results["score_aggregate"].values())
```
Add more tests!