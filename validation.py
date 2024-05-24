import ast
from games.greedy_pig.greedy_pig_sim import run_simulations
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
    league_folder = "games/greedy_pig/leagues/test_league"
    file_path = os.path.join(league_folder, f"{team_name}.py")
    with open(file_path, "w") as file:
        file.write(code)
    print("file written")
    #step 2 run 100 simulations
    try:
        results = run_simulations(100)
        print("simulations run")
        return results
    except Exception as e:
        print(e)
        return False
    finally:
        os.remove(file_path)
        print("file removed")
