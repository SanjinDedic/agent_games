"""Throwaway: rank validation players over many round-robins."""
from datetime import datetime, timedelta

from backend.database.db_models import League
from backend.games.breakthrough.breakthrough import BreakthroughGame

league = League(
    name="test_league",
    created_date=datetime.now(),
    expiry_date=datetime.now() + timedelta(days=7),
    game="breakthrough",
)

game = BreakthroughGame(league)
totals = {str(p.name): 0.0 for p in game.players}
wins = {str(p.name): 0 for p in game.players}
catches = {str(p.name): 0 for p in game.players}
breaks = {str(p.name): 0 for p in game.players}

ROUNDS = 40
for _ in range(ROUNDS):
    game.reset()
    r = game.play_game()
    for n, v in r["points"].items():
        totals[n] += v
    for n, v in r["table"]["wins"].items():
        wins[n] += v
    for n, v in r["table"]["catches"].items():
        catches[n] += v
    for n, v in r["table"]["breakthroughs"].items():
        breaks[n] += v

print(f"{'player':16} {'points':>10} {'wins':>6} {'catches':>8} {'breaks':>7}")
for n in sorted(totals, key=totals.get, reverse=True):
    print(f"{n:16} {totals[n]:10.0f} {wins[n]:6d} {catches[n]:8d} {breaks[n]:7d}")
