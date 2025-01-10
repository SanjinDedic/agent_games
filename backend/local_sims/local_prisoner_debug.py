import importlib.util
import os
import sys

# Add the project root directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
sys.path.append(backend_dir)

from database.db_models import League
from games.prisoners_dilemma.prisoners_dilemma import PrisonersDilemmaGame

# Set up the test league
test_league_folder = os.path.join(
    backend_dir, "games", "prisoners_dilemma", "leagues", "test_league"
)
test_league = League(
    folder=test_league_folder, name="Test League", game="prisoners_dilemma"
)


def safe_load_players(league_folder):
    players = []
    for item in os.listdir(league_folder):
        if item.endswith(".py"):
            module_name = item[:-3]
            module_path = os.path.join(league_folder, item)
            try:
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "CustomPlayer"):
                    player_class = getattr(module, "CustomPlayer")
                    player = player_class()
                    player.name = module_name
                    players.append(player)
            except Exception as e:
                print(f"Error loading player {module_name}: {str(e)}")
    return players


class SafePrisonersDilemmaGame(PrisonersDilemmaGame):
    def __init__(
        self,
        league,
        verbose=False,
        reward_matrix=None,
        rounds_per_pairing=5,
        collect_player_feedback=True,
    ):
        self.league = league
        self.verbose = verbose
        self.players = safe_load_players(
            os.path.join(backend_dir, "games", league.game, league.folder)
        )
        self.histories = {player.name: {} for player in self.players}
        self.reward_matrix = reward_matrix or {
            ("collude", "collude"): (4, 4),
            ("collude", "defect"): (0, 6),
            ("defect", "collude"): (6, 0),
            ("defect", "defect"): (0, 0),
        }
        self.rounds_per_pairing = rounds_per_pairing
        self.game_feedback = []
        self.player_feedback = []
        self.collect_player_feedback = collect_player_feedback
        self.scores = {player.name: 0 for player in self.players}


def run_simulation_excluding_team(game, excluded_team):
    try:
        # Create a new game instance with all players except the excluded one
        filtered_players = [p for p in game.players if p.name != excluded_team]
        filtered_game = SafePrisonersDilemmaGame(test_league)
        filtered_game.players = filtered_players
        filtered_game.histories = {player.name: {} for player in filtered_players}
        filtered_game.scores = {player.name: 0 for player in filtered_players}

        # Run a single simulation
        results = filtered_game.play_game()
        return "OK", results
    except Exception as e:
        return f"FAIL: {str(e)}", None


# Ask user if they want to see rankings
show_rankings = (
    input("Do you want to see rankings for each working simulation? (yes/no): ")
    .lower()
    .strip()
    == "yes"
)

# Create a base game instance with safely loaded players
base_game = SafePrisonersDilemmaGame(test_league)

print("\nRunning simulations excluding one team at a time:")
for player in base_game.players:
    result, game_results = run_simulation_excluding_team(base_game, player.name)
    print(f"Excluded: {player.name:<20} Result: {result}")

    if show_rankings and result == "OK":
        print("  Rankings:")
        sorted_scores = sorted(
            game_results["points"].items(), key=lambda x: x[1], reverse=True
        )
        for rank, (player_name, score) in enumerate(sorted_scores, 1):
            print(f"    {rank}. {player_name}: {score}")
    print()

print("All simulations completed.")
