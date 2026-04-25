from backend.games.greedy_pig.greedy_pig import GreedyPigGame
from backend.games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame


class GameFactory:
    @staticmethod
    def get_game_class(game_name):
        if game_name == "greedy_pig":
            return GreedyPigGame
        elif game_name == "prisoners_dilemma":
            return PrisonersDilemmaGame
        elif game_name == "lineup4":
            from backend.games.lineup4.lineup4 import Lineup4Game
            return Lineup4Game
        elif game_name == "arena_champions":
            from backend.games.arena_champions.arena_champions import ArenaChampionsGame
            return ArenaChampionsGame
        else:
            raise ValueError(f"Unknown game: {game_name}")

    @staticmethod
    def get_disallowed_attrs(game_name):
        if game_name == "greedy_pig":
            return ['banked_money', 'unbanked_money', 'has_banked_this_turn',
                    'color', 'name', 'feedback']
        elif game_name == "prisoners_dilemma":
            return ['name', 'feedback']
        elif game_name == "lineup4":
            return ['name', 'feedback', 'symbol', 'all_winning_sets']
        elif game_name == "arena_champions":
            # TODO: This isn't perfect as you can still change your attack proportion partway through a game
            return ['name', 'feedback', 'wins', 'losses', 'max_health',
                    'defense', 'strength', 'dexterity', 'attack']
        else:
            raise ValueError(f"Unknown game: {game_name}")
