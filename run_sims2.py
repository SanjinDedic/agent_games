import argparse
from multiple_players_game import run_simulation_many_times
from multiple_players_game import run_animation

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="Run game simulations.")

    # Add arguments
    parser.add_argument('-sims', type=int, required=True, help='Number of simulations to run')
    parser.add_argument('-refresh', type=int, required=True, help='refresh rate for animation')
    # Parse arguments
    args = parser.parse_args()

    run_animation(args.refresh, args.sims)

    # Run the simulation
    #results = run_simulation_many_times(args.sims)

    # Print results
    #print("Simulation Results:")
    #print(results)

if __name__ == "__main__":
    main()