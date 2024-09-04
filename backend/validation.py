import io
import sys
from contextlib import redirect_stdout
from games.base_game import BaseGame
from games.game_factory import GameFactory
from docker_simulation import run_docker_simulation
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


class ValidationSimulationError(Exception):
    pass

def run_validation_simulation(code, game_name, team_name):
    print("game_name in run_validation_simulation: ", game_name)
    test_league_folder = os.path.join(ROOT_DIR, 'games', game_name, 'leagues', 'test_league')
    test_league = League(folder=test_league_folder, name="Test League", game=game_name)

    file_path = os.path.join(ROOT_DIR, 'games', game_name, 'leagues', 'test_league', f"{team_name}.py")
    print(f"File path in validation.py: {file_path}")

    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as file:
            file.write(code)
        print(f"File written: {file_path}")
        is_successful, docker_result = run_docker_simulation('test_league', test_league.game, 'leagues/test_league', None, timeout=6, feedback_required=True)
        if not is_successful:
            if isinstance(docker_result, str):
                error_message = docker_result
            else:
                error_message = docker_result.get("message", "An unknown error occurred during the simulation.")
            print(f"Error message in validation.py: {error_message}")
            raise ValidationSimulationError(error_message)

        feedback = docker_result.get('feedback', 'No feedback available.')
        results = docker_result.get('simulation_results', {})

        return feedback, results
    except Exception as e:
        print(f"Error during simulation: {e}")
        raise ValidationSimulationError(str(e))
    finally:
        # Always attempt to remove the file, even if an exception occurred
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"File removed: {file_path}")
            except Exception as e:
                print(f"Error removing file: {e}")