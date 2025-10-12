#!/usr/bin/env python3
"""
Arena Champions Local Simulator
Runs all validation players against each other in a round-robin tournament.
Each player fights every other player twice (home and away).
Shows concise battle results and final win totals.
"""

import sys
import os
import itertools

# Add the backend directory to Python path so we can import the game modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.games.arena_champions.arena_champions import ArenaChampionsGame
from backend.games.arena_champions.validation_players import players


def run_battle(game, player1, player2):
    """Run a single battle between two players and return the result"""   
    winner, battle_result = game.execute_combat(player1, player2)
    final_health = battle_result.final_health

    player1_health = final_health.get(str(player1.name), 0)
    player2_health = final_health.get(str(player2.name), 0)

    # Debug: detect if an attacker self-KO'd due to big_attack
    for turn in battle_result.turns:
        try:
            if turn.get("attack_action") == "big_attack":
                attacker_name = turn.get("attacker")
                defender_name = turn.get("defender")
                hb = turn.get("health_before", {})
                ha = turn.get("health_after", {})
                attacker_before = hb.get(attacker_name, 0)
                attacker_after = ha.get(attacker_name, 0)
                defender_after = ha.get(defender_name, 0)
                # In these mechanics, only big_attack can reduce the attacker's HP on their own turn
                if attacker_after <= 0:
                    double_ko = defender_after <= 0
                    print(
                        f"[SELF-KO DEBUG] Turn {turn.get('turn')} | {attacker_name} used big_attack and self-damaged to KO. "
                        f"HP {attacker_before:.1f} -> {attacker_after:.1f}. {defender_name} HP after: {defender_after:.1f}."
                    )
                    if double_ko:
                        print(
                            f"[SELF-KO DEBUG] DOUBLE-KO detected. Per tie rule, winner is the SECOND player passed to execute_combat: {battle_result.player2}. Declared winner: {battle_result.winner or winner}."
                        )
                    else:
                        print(
                            f"[SELF-KO DEBUG] Attacker KO'd themselves; defender should win. Declared winner: {battle_result.winner or winner}."
                        )
        except Exception:
            # Be resilient to any unexpected battle_result format issues
            pass

    # If both are KO'd at battle end, print an explicit tie-break summary
    if player1_health <= 0 and player2_health <= 0:
        print(
            f"[BATTLE SUMMARY] DOUBLE-KO: {battle_result.player1} and {battle_result.player2} are both <= 0 HP. "
            f"Tie rule awards the win to the SECOND player passed to execute_combat: {battle_result.player2}. Declared winner: {winner}."
        )

    return winner, player1_health, player2_health


def main():
    """Main simulation function"""
    print("Arena Champions Round-Robin Tournament Simulator")
    print("===============================================")
    print("Every player fights every other player twice (home and away)")
    print()

    # Create a minimal game instance for combat mechanics
    class SimpleLeague:
        def __init__(self):
            pass

    game = ArenaChampionsGame(SimpleLeague(), verbose=False)

    # Track wins for each player
    win_counts = {str(player.name): 0 for player in players}
    total_battles = 0

    print("Battle Results:")
    print("-" * 60)

    # Fight each pair twice (home and away)
    for player1, player2 in itertools.combinations(players, 2):
        # Reset players to original stats before each battle
        player1.set_to_original_stats()
        player2.set_to_original_stats()

        # Battle 1: player1 goes first
        winner, p1_health, p2_health = run_battle(game, player1, player2)
        print(f"{player1.name}(H) vs {player2.name}(A) | {winner} WON | {player1.name}: {p1_health:.1f} HP | {player2.name}: {p2_health:.1f} HP")
        win_counts[winner] += 1
        total_battles += 1

        # Reset players again
        player1.set_to_original_stats()
        player2.set_to_original_stats()

        # Battle 2: player2 goes first
        winner, p2_health, p1_health = run_battle(game, player2, player1)
        # Note: battle_result uses player order as passed to execute_combat
        # So we need to swap the health values for display
        print(f"{player2.name}(H) vs {player1.name}(A) | {winner} WON | {player1.name}: {p1_health:.1f} HP | {player2.name}: {p2_health:.1f} HP")
        win_counts[winner] += 1
        total_battles += 1

    # Display final results
    print("\n" + "=" * 60)
    print("FINAL TOURNAMENT RESULTS (Single Round-Robin)")
    print("=" * 60)
    print(f"Total battles fought: {total_battles}")
    print("\nWin counts:")

    # Sort players by wins (descending)
    sorted_players = sorted(win_counts.items(), key=lambda x: x[1], reverse=True)

    # Each player battles every other player twice (home and away)
    battles_per_player = 2 * (len(players) - 1)

    for rank, (player_name, wins) in enumerate(sorted_players, 1):
        # Guard against division by zero if there are fewer than 2 players
        win_percentage = (
            (wins / battles_per_player) * 100 if battles_per_player > 0 else 0
        )
        print(f"{rank:2d}. {player_name:<20} {wins:2d} wins ({win_percentage:.1f}%)")

    # Now run 100 simulations to level out dodge performance
    print("\n" + "=" * 80)
    print("RUNNING 1000 SIMULATIONS TO LEVEL OUT DODGE PERFORMANCE...")
    print("=" * 80)
    print("This may take a moment...")

    # Create a proper league instance for simulations
    class SimulationLeague:
        def __init__(self):
            pass

    # Run the simulations using the game's built-in method
    sim_game = ArenaChampionsGame(SimulationLeague(), verbose=False)
    sim_game.players = players  # Set the players
    sim_results = sim_game.run_simulations(1000, SimulationLeague())

    print("\n" + "=" * 60)
    print("FINAL RESULTS AFTER 1000 SIMULATIONS")
    print("=" * 60)
    print(f"Total simulations run: {sim_results['num_simulations']}")
    print("\nTotal wins across all simulations:")

    # Sort by total wins across all simulations
    sim_sorted = sorted(sim_results['total_points'].items(), key=lambda x: x[1], reverse=True)

    for rank, (player_name, total_wins) in enumerate(sim_sorted, 1):
        avg_wins = sim_results['table']['avg_wins_per_sim'][player_name]
        print(f"{rank:2d}. {player_name:<20} {total_wins:3d} total wins ({avg_wins:.2f} avg per sim)")

    print("\nSimulation complete!")


if __name__ == "__main__":
    main()
