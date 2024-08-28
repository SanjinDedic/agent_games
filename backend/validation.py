import io
import sys
from contextlib import redirect_stdout
from games.base_game import BaseGame
from games.game_factory import GameFactory
from models_db import League
from utils import get_games_names
from config import ROOT_DIR
import os
import ast


# List of allowed modules and their allowed sub-modules
# Dynamically generate the ALLOWED_MODULES dictionary
ALLOWED_MODULES = {
    'random': None,  # None means no specific sub-modules are allowed
    'games': {game_name: {'player': None} for game_name in get_games_names()},
    'player': None  # Allow direct import from player
}

# List of risky functions
RISKY_FUNCTIONS = ['eval', 'exec', 'open', 'compile', 'execfile', 'input']

class SafeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.safe = True

    def visit_Import(self, node):
        for alias in node.names:
            if not self.is_allowed_import(alias.name):
                self.safe = False
                return
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if not self.is_allowed_import(node.module, node.names[0].name):
            self.safe = False
            return
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in RISKY_FUNCTIONS:
            self.safe = False
            return
        self.generic_visit(node)

    def is_allowed_import(self, module, submodule=None):
        parts = module.split('.')
        current = ALLOWED_MODULES
        for part in parts:
            if part not in current:
                return False
            if current[part] is None:
                return True
            current = current[part]
        
        if submodule:
            return submodule in current
        return True

def is_agent_safe(code):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    checker = SafeVisitor()
    checker.visit(tree)
    return checker.safe

def run_agent_simulation(code, game_name, team_name):
    print("game_name in run_agent_simulation: ", game_name)
    test_league_folder = os.path.join(ROOT_DIR, 'games', game_name, 'leagues', 'test_league')
    test_league = League(folder=test_league_folder, name="Test League", game=game_name)
    
    file_path = os.path.join(ROOT_DIR, 'games', game_name, 'leagues', 'test_league', f"{team_name}.py")
    print("Root dir in validation.py: ", ROOT_DIR)
    print(f"File path in validation.py: {file_path}")

    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as file:
            file.write(code)
        print(f"File written: {file_path}")

        game_class = GameFactory.get_game_class(game_name)
        
        # Run one game in verbose mode and capture the output
        f = io.StringIO()
        with redirect_stdout(f):
            game = game_class(test_league, verbose=True)
            game.play_game()
        feedback = f.getvalue()
        print("Feedback: ", feedback)
        # Run multiple simulations for the actual results
        results = game_class.run_simulations(100, test_league) #needs to be docker_simulation (just testing CI/CD lol)
        print("Simulations run")
        print(results)
        return results, feedback
    except Exception as e:
        print(f"Error during simulation: {e}")
        return False, str(e)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"File removed: {file_path}")
