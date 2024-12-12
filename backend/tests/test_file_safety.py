from validation import is_agent_safe


def test_is_safe():
    safe_code = """
from player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 15:
            return 'bank'
        return 'continue'
"""
    assert is_agent_safe(safe_code) is True

    unsafe_code_import = """
import os

class CustomPlayer(Player):
    def make_decision(self, game_state):
        os.system('rm -rf /')
        return 'continue'
"""
    assert is_agent_safe(unsafe_code_import) is False

    unsafe_code_exec = """
class CustomPlayer(Player):
    def make_decision(self, game_state):
        exec('print("Hello, world!")')
        return 'continue'
"""
    assert is_agent_safe(unsafe_code_exec) is False
