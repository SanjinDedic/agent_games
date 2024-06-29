import ast
import os
from games.base_game import BaseGame
from games.game_factory import GameFactory
from models_db import League

# List of dangerous modules and risky functions
DANGEROUS_MODULES = ['os', 'sys', 'subprocess', 'shutil']
RISKY_FUNCTIONS = ['eval', 'exec', 'open', 'compile', 'execfile', 'input']

class SafeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.safe = True

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name.split('.')[0] in DANGEROUS_MODULES:
                self.safe = False
                return
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module and node.module.split('.')[0] in DANGEROUS_MODULES:
            self.safe = False
            return
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in RISKY_FUNCTIONS:
            self.safe = False
            return
        self.generic_visit(node)

def is_agent_safe(code):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    checker = SafeVisitor()
    checker.visit(tree)
    return checker.safe

def run_agent_simulation(code, game_name, team_name):
    test_league_folder = "leagues/test_league"
    test_league = League(folder=test_league_folder, name="Test League", game=game_name)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'games', game_name, test_league.folder, f"{team_name}.py")
    
    try:
        with open(file_path, "w") as file:
            file.write(code)
        print(f"File written: {file_path}")

        game_class = GameFactory.get_game_class(game_name)
        results = BaseGame.run_simulations(500, game_class, test_league)
        print("Simulations run")
        print(results)
        return results
    except Exception as e:
        print(f"Error during simulation: {e}")
        return False
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"File removed: {file_path}")

def ensure_test_league_folder(game_name):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_league_folder = os.path.join(current_dir, 'games', game_name, 'leagues', 'test_league')
    os.makedirs(test_league_folder, exist_ok=True)
    return test_league_folder