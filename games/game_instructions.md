# Creating a New Game for agent_games

This guide will walk you through the process of creating a new game for the agent_games project. By following these steps, you'll be able to implement a game that integrates seamlessly with the existing framework.

## Table of Contents

1. [Create the Game Directory](#1-create-the-game-directory)
2. [Implement the Game Class](#2-implement-the-game-class)
3. [Create the Player Class](#3-create-the-player-class)
4. [Update the Game Factory](#4-update-the-game-factory)
5. [Add Game-Specific Files](#5-add-game-specific-files)
6. [Testing Your Game](#6-testing-your-game)
7. [Documentation](#7-documentation)

## 1. Create the Game Directory

First, create a new directory for your game inside the `games` folder. Name it after your game, using snake_case.

```
agent_games/
└── games/
    └── your_game_name/
```

## 2. Implement the Game Class

Create a new Python file in your game directory, named after your game (e.g., `your_game_name.py`). In this file, implement your game class, which should inherit from `BaseGame`.

```python
from games.base_game import BaseGame
import random

class YourGameName(BaseGame):
    starter_code = '''
# Provide starter code for players here
'''

    game_instructions = '''
# Provide HTML-formatted game instructions here
'''

    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)
        # Initialize game-specific attributes here

    def play_round(self):
        # Implement the logic for a single round of the game

    def get_game_state(self):
        # Return the current state of the game

    def play_game(self, custom_rewards=None):
        # Implement the full game logic
        # Return the results in the format: {"points": points, "score_aggregate": scores}

    def assign_points(self, scores, custom_rewards=None):
        # Implement the point assignment logic

    def reset(self):
        super().reset()
        # Reset any game-specific attributes

def run_simulations(num_simulations, league, custom_rewards=None):
    return BaseGame.run_simulations(num_simulations, YourGameName, league, custom_rewards)
```

Ensure that you implement all the required methods, including `play_round`, `get_game_state`, `play_game`, `assign_points`, and `reset`.

## 3. Create the Player Class

Create a `player.py` file in your game directory to define the base `Player` class for your game.

```python
from abc import ABC, abstractmethod

class Player(ABC):
    def __init__(self):
        self.name = None
        # Initialize any player-specific attributes

    @abstractmethod
    def make_decision(self, game_state):
        pass
    
    # Add any helper methods that players might need
```

## 4. Update the Game Factory

Update the `game_factory.py` file in the `games` directory to include your new game:

```python
from games.greedy_pig.greedy_pig import GreedyPigGame
from games.forty_two.forty_two import FortyTwoGame
from games.your_game_name.your_game_name import YourGameName

class GameFactory:
    @staticmethod
    def get_game_class(game_name):
        if game_name == "greedy_pig":
            return GreedyPigGame
        elif game_name == "forty_two":
            return FortyTwoGame
        elif game_name == "your_game_name":
            return YourGameName
        else:
            raise ValueError(f"Unknown game: {game_name}")
```

## 5. Add Game-Specific Files

If your game requires any additional files (e.g., game assets, configuration files), add them to your game directory.

## 6. Testing Your Game

Create test files for your game in the `tests` directory. At minimum, you should have:

- `test_your_game_name.py`: Unit tests for your game logic
- Update `test_api_sim.py` to include tests for your game's API integration

## 7. Documentation

Update the project documentation to include information about your new game:

- Add a section in the README.md file describing your game
- Update any relevant API documentation
- If necessary, create a separate markdown file with detailed game rules and strategies

By following these steps, you'll create a new game that integrates well with the existing agent_games framework. Remember to maintain consistency with the existing code style and structure throughout your implementation.