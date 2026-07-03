"""AST safety check for submitted agent code.

Runs in the API process before enqueue — unsafe code never reaches a worker.
The Celery task that actually executes the agent lives in
backend/tasks/validation_task.py.
"""

import ast
from typing import Optional, Tuple

# Security configuration
ALLOWED_MODULES = {
    "random": None,
    "string": None,
    "math": None,
    "games": None,
    "player": None,
}

RISKY_FUNCTIONS = [
    "eval",
    "exec",
    "open",
    "compile",
    "execfile",
    "input",
    "os",
    "sys",
    "subprocess",
    "importlib",
    "__import__",
]


class CodeValidator(ast.NodeVisitor):
    """AST visitor for validating code safety"""

    def __init__(self):
        self.safe = True
        self.error_message = None

    def visit_Import(self, node):
        for alias in node.names:
            if not self._is_allowed_import(alias.name):
                self.safe = False
                self.error_message = f"Unauthorized import: {alias.name}"
                return
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if not self._is_allowed_import(node.module, node.names[0].name):
            self.safe = False
            self.error_message = (
                f"Unauthorized import: {node.module}.{node.names[0].name}"
            )
            return
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in RISKY_FUNCTIONS:
            self.safe = False
            self.error_message = f"Unauthorized function call: {node.func.id}"
            return
        self.generic_visit(node)

    def _is_allowed_import(self, module: str, submodule: str = None) -> bool:
        parts = module.split(".")
        current = ALLOWED_MODULES
        for part in parts:
            if part not in current:
                return False
            if current[part] is None:
                return True
            current = current[part]
        return submodule in current if submodule else True


def validate_code(code: str) -> Tuple[bool, Optional[str]]:
    """Validate code safety using AST analysis"""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error in code: {str(e)}"

    validator = CodeValidator()
    validator.visit(tree)
    return validator.safe, validator.error_message
