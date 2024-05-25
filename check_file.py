import ast

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

def is_safe(code):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    checker = SafeVisitor()
    checker.visit(tree)
    return checker.safe
