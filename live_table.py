import argparse
from game_simulation import GameSimulation

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="Run game simulations.")

    # Add arguments
    parser.add_argument('-sims', type=int, required=True, help='Number of simulations to run')
    parser.add_argument('-refresh', type=int, required=False, help='refresh rate for animation')
    parser.add_argument('-folder', type=str, required=False, help='folder for which classes to run')
    # Parse arguments
    args = parser.parse_args()
    simulation = GameSimulation()
    simulation.set_folder(args.folder)
    simulation.run_simulation_with_animation(number = args.sims, refresh_rate = args.refresh)


if __name__ == "__main__":
    main()