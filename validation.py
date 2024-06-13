import ast
from games.greedy_pig.greedy_pig_sim import run_simulations
from models_db import League
import os

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

def run_agent_simulation(code, team_name):
    test_league_folder = "leagues/test_league"

    test_league = League(folder=test_league_folder, name="Test League")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if test_league.game == "greedy_pig":
        file_path = os.path.join(current_dir,'games', 'greedy_pig', test_league.folder, f"{team_name}.py")
        print("greedy pig file path", file_path)
    else:
        file_path = os.path.join(current_dir,'games', 'greedy_pig', test_league.folder, f"{team_name}.py")
    print("file path ATTEMPT TO WRITE", file_path)
    with open(file_path, "w") as file:
        file.write(code)
    print("file written")
    #step 2 run 100 simulations
    try:
        results = run_simulations(500, test_league)
        print("simulations run")
        print(results)
        return results
    except Exception as e:
        print(e)
        return False
    finally:
        os.remove(file_path)
        print("file removed", file_path)
