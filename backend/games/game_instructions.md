# Creating a New Game for agent_games

## Part 1: General Instructions

1. **Create the Game Directory**
   Create a new directory in the `games` folder with this structure:

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
   - Create a Python file named after your game (e.g., `your_game_name.py`)
   - Inherit from `BaseGame`
   - Implement required methods:
     - `play_game()`: Main game logic
     - `get_game_state()`: Current game state
     - `run_simulations()`: Run multiple games
   - Include game feedback system:
     - Use `self.game_feedback` for overall game progress
     - Support both string (markdown) and dictionary feedback formats
     - Add round-by-round state updates and important events

3. **Implement Player Feedback**
   - Use `player.add_feedback()` for player-specific messages
   - Store feedback in `self.player_feedback`
   - Support both simple messages and structured data
   - Example feedback formats:

   ```python
   # String/Markdown format
   self.add_feedback("## Round 1\n- Player chose action: move_left")

   # Dictionary format
   self.add_feedback({
       "round": 1,
       "action": "move_left",
       "state": {"position": [0, 1], "score": 10}
   })
   ```

4. **Create the Player Class**
   - Create `player.py` with a base `Player` class
   - Include feedback functionality:
     ```python
     class Player(ABC):
         def __init__(self):
             self.feedback = []

         def add_feedback(self, message):
             self.feedback.append(message)

         @abstractmethod
         def make_decision(self, game_state):
             pass
     ```

5. **Update Game Factory**
   - Add your game to `game_factory.py`
   - Include proper imports and game class registration

6. **Add Test League Bots**
   - Create example bots in `test_league` folder
   - Demonstrate feedback usage in example bots

7. **Create Unit Tests**
   - Test game logic and scoring
   - Verify feedback functionality:
     ```python
     def test_game_feedback(test_league):
         game = YourGame(test_league, verbose=True)
         results = game.play_game()
         assert "feedback" in results
         assert isinstance(results["feedback"], (str, dict))
     ```

## Part 2: Example - AlphaGuess Implementation

Here's a simplified example showing feedback implementation:

```python
class AlphaGuessGame(BaseGame):
    def __init__(self, league, verbose=False):
        super().__init__(league, verbose)
        self.game_feedback = []
        self.player_feedback = {}

    def play_round(self):
        self.correct_letter = random.choice(string.ascii_lowercase)
        self.add_feedback(f"## Round {self.round_number}")
        
        for player in self.players:
            guess = player.make_decision(self.get_game_state())
            self.add_feedback(f"- {player.name} guessed: {guess}")
            
            if guess == self.correct_letter:
                self.scores[player.name] += 1
                self.add_feedback(f"  ✓ Correct!")
            
            # Collect player feedback
            if player.feedback:
                self.player_feedback[player.name] = player.feedback
                player.feedback = []

    @classmethod
    def run_single_game_with_feedback(cls, league):
        game = cls(league, verbose=True)
        results = game.play_game()
        return {
            "results": results,
            "feedback": "\n".join(game.game_feedback),
            "player_feedback": game.player_feedback
        }
```

8. **Documentation Requirements**
   - Include clear game rules and objectives
   - Document feedback formats and usage
   - Provide example bot implementations
   - Add setup and testing instructions

Remember:
- Keep feedback informative but concise
- Use markdown formatting for string feedback
- Structure dictionary feedback logically
- Clear player feedback between rounds
- Test both feedback formats thoroughly