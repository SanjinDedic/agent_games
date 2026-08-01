import importlib
import inspect

from backend.config import GAMES
from backend.games.base_game import BaseGame


class GameFactory:
    _cache = {}

    @staticmethod
    def get_game_class(game_name):
        """Dynamically resolve a game's BaseGame subclass by folder name.

        Convention: backend/games/<game_name>/<game_name>.py must define
        exactly one subclass of BaseGame.
        """
        if game_name in GameFactory._cache:
            return GameFactory._cache[game_name]

        if game_name not in GAMES:
            raise ValueError(f"Unknown game: {game_name}")

        try:
            module = importlib.import_module(
                f"backend.games.{game_name}.{game_name}"
            )
        except ModuleNotFoundError as e:
            raise ValueError(f"Unknown game: {game_name}") from e

        for attr in vars(module).values():
            if (
                inspect.isclass(attr)
                and issubclass(attr, BaseGame)
                and attr is not BaseGame
                and attr.__module__ == module.__name__
            ):
                GameFactory._cache[game_name] = attr
                return attr

        raise ValueError(
            f"No BaseGame subclass found in backend.games.{game_name}.{game_name}"
        )
