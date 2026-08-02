"""Tests for the AST safety gate (backend/routes/user/code_validation.py).

The execution semantics of validation itself live in
backend/tests/unit/test_validation_executor.py (direct + isolated runs) and
backend/tests/unit/test_validation_client.py (Lambda/local dispatch); this
file covers only the pre-execution gate that runs in the API process.
"""

import ast

from backend.routes.user.code_validation import CodeValidator, validate_code

# Resource-exhaustion agents that are AST-clean by design: no blocked imports
# or calls, so they genuinely reach the execution sandbox — whose fork
# isolation and hard kill (test_validation_executor.py) are what contain them.
MEMORY_BOMB_RECURSION = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    _hoard = []

    def make_decision(self, game_state):
        def grow(chunk):
            CustomPlayer._hoard.append(chunk)   # pin it so it can't be freed
            return grow(chunk + chunk)          # double every frame
        grow(bytearray(1024 * 1024))            # start at 1 MB
        return "bank"
"""

CPU_BOMB = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        while True:
            try:
                n = 0
                for i in range(10 ** 8):
                    n += i * i
            except Exception:
                continue
"""


def test_hostile_agents_pass_the_ast_check():
    """Both bombs are 'safe' by AST rules — containment is the sandbox's job
    (hard kill / Lambda memory cap), not the gate's."""
    for code in (MEMORY_BOMB_RECURSION, CPU_BOMB):
        is_safe, message = validate_code(code)
        assert is_safe, f"expected AST-clean, got: {message}"


def test_validate_code_syntax_error():
    """Invalid syntax is caught by the pre-execution AST check"""
    is_safe, message = validate_code("This is not valid Python code")
    assert not is_safe
    assert "syntax error" in message.lower()


def test_code_validator_success():
    """Test successful code validation scenarios"""
    validator = CodeValidator()

    # Test case 1: Valid imports
    code = "import random\nimport math"
    tree = ast.parse(code)
    validator.visit(tree)
    assert validator.safe
    assert validator.error_message is None

    # Test case 2: Valid code with allowed functionality
    code = """
from games.prisoners_dilemma.player import Player
class CustomPlayer(Player):
    def make_decision(self, game_state):
        return random.choice(['collude', 'defect'])
"""
    tree = ast.parse(code)
    validator.safe = True  # Reset for new test
    validator.visit(tree)
    assert validator.safe


def test_code_validator_exceptions():
    """Test code validator error cases"""
    validator = CodeValidator()

    # Test case 1: Unauthorized import
    code = "import os"
    tree = ast.parse(code)
    validator.visit(tree)
    assert not validator.safe
    assert "unauthorized import" in validator.error_message.lower()

    # Test case 2: Unauthorized from import
    code = "from os import system"
    tree = ast.parse(code)
    validator.safe = True  # Reset for new test
    validator.visit(tree)
    assert not validator.safe
    assert "unauthorized import" in validator.error_message.lower()

    # Test case 3: Unauthorized function call (eval)
    code = "eval('1 + 1')"
    tree = ast.parse(code)
    validator.safe = True  # Reset for new test
    validator.visit(tree)
    assert not validator.safe
    assert "unauthorized function" in validator.error_message.lower()

    # Test case 4: Unauthorized function call (exec)
    code = "exec('print(\"hello\")')"
    tree = ast.parse(code)
    validator.safe = True  # Reset for new test
    validator.visit(tree)
    assert not validator.safe
    assert "unauthorized function" in validator.error_message.lower()
