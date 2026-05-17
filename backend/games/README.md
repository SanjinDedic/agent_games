# Adding a New Game

Games are auto-discovered. Drop the right files in the right folders and they light up — no edits to `config.py`, `game_factory.py`, or any frontend registry needed.

## Backend — 3 files in `backend/games/<game_name>/`

Folder name **is** the game's identifier (snake_case, used in URLs, league records, and feedback payloads). The folder must contain exactly these three files:

| File | Purpose |
|------|---------|
| `player.py` | Abstract `Player` base class students subclass |
| `<game_name>.py` | Game class extending `BaseGame` — must contain exactly one `BaseGame` subclass |
| `validation_players.py` | Sample players used by the validator to test submissions |

An `__init__.py` is optional (most existing games have an empty one — fine either way).

### `player.py`

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

### `<game_name>.py`

Subclass `BaseGame`. Set `game_instructions` (HTML shown in editor) and `starter_code` (skeleton students see). Implement `play_game` and `run_simulations`. See `greedy_pig/greedy_pig.py` for a minimal worked example.

Return dict from `run_simulations` must include `total_points` and `num_simulations`; optional `table` keys become extra columns in the default results display.

### `validation_players.py`

Module-level `players = [Instance1(), Instance2(), ...]` — the validator runs new submissions against this list.

```python
from backend.games.<game_name>.player import Player

class Simple(Player):
    def make_decision(self, game_state):
        return ...

players = [Simple()]
```

### Discovery

`backend/config.py::_discover_games` scans `backend/games/*/` and accepts any folder containing all three files. `GameFactory.get_game_class(name)` imports `backend.games.<name>.<name>` and returns the single `BaseGame` subclass it finds.

## Frontend — 1 folder in `frontend/src/AgentGames/Feedback/games/<game_name>/`

The folder must export a manifest at `index.jsx`:

```jsx
import MyGameFeedback from './MyGameFeedback';

export default {
  name: 'my_game',                     // must match backend folder name
  displayName: 'My Game',              // shown on cards and headings
  description: 'Long blurb for the homepage card.',
  shortDescription: 'Tight blurb for the demo panel.',  // optional
  thumbnail: 'games/my_game.png',      // S3 path under VITE_ASSETS_URL/images/
  featured: true,                      // show on AgentHome + Demo
  order: 5,                            // sort key for card grids
  Feedback: MyGameFeedback,            // component receives { feedback }
  ResultsDisplay: null,                // optional; null = default ResultsDisplay
};
```

`frontend/src/AgentGames/Feedback/games/index.jsx` collects every subfolder's `index.jsx` via `import.meta.glob`. The collected map drives:

- **`FeedbackRegistry`** — looks up `Feedback` component by `feedback.game`
- **`GameResultsWrapper`** — looks up optional `ResultsDisplay` by `currentLeague.game`
- **`AgentHome` + `Demo`** — iterate `featuredGames` to render the card grids

### Feedback component

Receives one prop: `feedback` (the dict the game emits in `game_feedback`). Game feedback payloads must include `game: '<game_name>'` so the registry routes them — `BaseGame` already sets this for you.

### Optional `ResultsDisplay`

Only override when the default `Shared/Utilities/ResultsDisplay` table doesn't fit (e.g. lineup4 wins/losses, arena champions per-round scoring). See `lineup4/Lineup4ResultsDisplay.jsx`.

### Thumbnail

Upload PNG to S3 (or whatever `VITE_ASSETS_URL` points at) under `images/games/<game_name>.png`. The manifest's `thumbnail` field is passed straight to `imageUrl(...)`.

## End-to-end checklist for a new game

1. `mkdir backend/games/my_game/`
2. Add `player.py`, `my_game.py`, `validation_players.py`
3. Restart API + validator + simulator (Docker picks up the new files; no `game_factory` edit)
4. `mkdir frontend/src/AgentGames/Feedback/games/my_game/`
5. Add `MyGameFeedback.jsx` and `index.jsx`
6. Upload `images/games/my_game.png` to assets bucket
7. Reload the frontend — homepage card, demo panel, league dropdown, feedback rendering all light up

## Notes

- `backend/games/game_instructions.md` is the older walkthrough — kept for reference but predates auto-discovery. Trust this README.
- Tests run via Docker compose — see top-level `CLAUDE.md`.
- Game-name convention: snake_case folder, matching `.py` module name, matching `feedback.game` string. Don't drift.
