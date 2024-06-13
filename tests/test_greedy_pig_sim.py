import os
import sys
import pytest
import time
from io import StringIO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from games.greedy_pig.greedy_pig_sim import draw_table, animate_simulations
from games.greedy_pig.greedy_pig import Game
from models_db import League

def test_draw_table(capsys):
    rankings = [
        ("Player1", 100),
        ("Player2", 90),
        ("Player3", 80),
        ("Player4", 70),
    ]

    draw_table(rankings)
    captured = capsys.readouterr()

    # Remove extra whitespace from the captured output
    lines = [line.strip() for line in captured.out.split('\n')]

    assert lines[0] == "-" * 50
    assert "Player1" in lines[3]
    assert "Player2" in lines[4]
    assert "Player3" in lines[5]
    assert "Player4" in lines[6]

def test_animate_simulations(capsys):
    num_simulations = 5
    refresh_number = 2

    # Create a dummy League object for testing
    test_league = League(folder="leagues/test_league", name="Test League")
    game = Game(test_league)
    animate_simulations(num_simulations, refresh_number, game)
    captured = capsys.readouterr()

    assert "Rankings after 2 simulations:" in captured.out
    assert "Rankings after 4 simulations:" in captured.out
    assert "Rankings after 5 simulations:" in captured.out