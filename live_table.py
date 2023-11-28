import argparse
from animated_multi_player_game import run_simulation_with_animation

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="Run game simulations.")

    # Add arguments
    parser.add_argument('-sims', type=int, required=True, help='Number of simulations to run')
    parser.add_argument('-refresh', type=int, required=False, help='refresh rate for animation')
    parser.add_argument('-folder', type=str, required=False, help='folder for which classes to run')
    # Parse arguments
    args = parser.parse_args()

    run_simulation_with_animation(number = args.sims, refresh_rate = args.refresh, folder_name = args.folder)

    # Run the simulation
    #results = run_simulation_many_times(args.sims)
    #top 5 nth times
    # Print results
    #print("Simulation Results:")
    #print(results)

if __name__ == "__main__":
    main()