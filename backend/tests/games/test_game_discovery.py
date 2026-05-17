import importlib
import shutil
import sys
from pathlib import Path

import pytest

from backend.config import GAMES, ROOT_DIR, _discover_games
from backend.games.base_game import BaseGame
from backend.games.game_factory import GameFactory

GAMES_DIR = Path(ROOT_DIR) / "games"


# ---------------------------------------------------------------------------
# _discover_games — pure filesystem scan
# ---------------------------------------------------------------------------


def test_discover_returns_known_games():
    found = _discover_games(str(GAMES_DIR))
    for name in ("greedy_pig", "prisoners_dilemma", "lineup4", "arena_champions"):
        assert name in found


def test_discover_is_sorted():
    found = _discover_games(str(GAMES_DIR))
    assert found == sorted(found)


def test_discover_matches_config_GAMES():
    assert set(GAMES) == set(_discover_games(str(GAMES_DIR)))


def test_discover_missing_dir_returns_empty(tmp_path):
    assert _discover_games(str(tmp_path / "does_not_exist")) == []


def _make_game(root, name, files):
    d = root / name
    d.mkdir()
    for f in files:
        (d / f).write_text("")


def test_discover_requires_all_three_files(tmp_path):
    _make_game(tmp_path, "complete", ["player.py", "complete.py", "validation_players.py"])
    _make_game(tmp_path, "missing_player", ["complete.py", "validation_players.py"])
    _make_game(tmp_path, "missing_main", ["player.py", "validation_players.py"])
    _make_game(tmp_path, "missing_validation", ["player.py", "missing_validation.py"])
    _make_game(
        tmp_path,
        "wrong_main_name",
        ["player.py", "other_name.py", "validation_players.py"],
    )
    found = _discover_games(str(tmp_path))
    assert found == ["complete"]


def test_discover_ignores_underscore_and_hidden_prefixes(tmp_path):
    _make_game(tmp_path, "_private", ["player.py", "_private.py", "validation_players.py"])
    _make_game(tmp_path, ".hidden", ["player.py", ".hidden.py", "validation_players.py"])
    _make_game(tmp_path, "real", ["player.py", "real.py", "validation_players.py"])
    found = _discover_games(str(tmp_path))
    assert found == ["real"]


def test_discover_ignores_loose_files(tmp_path):
    (tmp_path / "stray.py").write_text("")
    _make_game(tmp_path, "real", ["player.py", "real.py", "validation_players.py"])
    found = _discover_games(str(tmp_path))
    assert found == ["real"]


# ---------------------------------------------------------------------------
# GameFactory.get_game_class — dynamic import + BaseGame reflection
# ---------------------------------------------------------------------------


def test_factory_returns_known_game_class():
    cls = GameFactory.get_game_class("greedy_pig")
    assert cls.__name__ == "GreedyPigGame"
    assert issubclass(cls, BaseGame)


def test_factory_unknown_game_raises():
    with pytest.raises(ValueError, match="Unknown game"):
        GameFactory.get_game_class("not_a_real_game_xyz")


def test_factory_caches_result():
    a = GameFactory.get_game_class("greedy_pig")
    b = GameFactory.get_game_class("greedy_pig")
    assert a is b


# ---------------------------------------------------------------------------
# GameFactory — temp game folder fixtures for negative / positive dynamic cases
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_game_folder(monkeypatch):
    """Create temp game folder(s) inside backend/games/ and clean up after."""
    created = []

    def _make(name, main_body):
        game_dir = GAMES_DIR / name
        if game_dir.exists():
            raise RuntimeError(f"temp game folder already exists: {game_dir}")
        game_dir.mkdir()
        (game_dir / "__init__.py").write_text("")
        (game_dir / "player.py").write_text("")
        (game_dir / "validation_players.py").write_text("players = []\n")
        (game_dir / f"{name}.py").write_text(main_body)
        created.append(game_dir)
        importlib.invalidate_caches()
        # Allow factory to find the new game without restarting.
        monkeypatch.setattr(
            "backend.games.game_factory.GAMES",
            list(GAMES) + [g.name for g in created],
        )
        return game_dir

    yield _make

    for game_dir in created:
        prefix = f"backend.games.{game_dir.name}"
        for mod in list(sys.modules):
            if mod == prefix or mod.startswith(prefix + "."):
                del sys.modules[mod]
        GameFactory._cache.pop(game_dir.name, None)
        shutil.rmtree(game_dir, ignore_errors=True)


def test_factory_raises_when_no_basegame_subclass(temp_game_folder):
    temp_game_folder(
        "dummy_no_subclass_xyz",
        "VALUE = 1\n",
    )
    with pytest.raises(ValueError, match="No BaseGame subclass"):
        GameFactory.get_game_class("dummy_no_subclass_xyz")


def test_factory_loads_dynamically_added_game(temp_game_folder):
    temp_game_folder(
        "dummy_valid_game_xyz",
        (
            "from backend.games.base_game import BaseGame\n"
            "class DummyValidGameXyz(BaseGame):\n"
            "    starter_code = ''\n"
            "    game_instructions = ''\n"
        ),
    )
    cls = GameFactory.get_game_class("dummy_valid_game_xyz")
    assert cls.__name__ == "DummyValidGameXyz"
    assert issubclass(cls, BaseGame)


def test_factory_ignores_imported_basegame_subclasses(temp_game_folder):
    """Only subclasses defined in the game's own module count.

    The factory filters by `attr.__module__ == module.__name__` so a re-export
    of an existing game class won't be picked up.
    """
    temp_game_folder(
        "dummy_reexport_xyz",
        (
            "from backend.games.greedy_pig.greedy_pig import GreedyPigGame\n"
            "ALIAS = GreedyPigGame\n"
        ),
    )
    with pytest.raises(ValueError, match="No BaseGame subclass"):
        GameFactory.get_game_class("dummy_reexport_xyz")
