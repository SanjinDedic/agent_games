import argparse
from multiple_players_game_nathan import run_simulation_many_times

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="Run game simulations.")

    # Add arguments
    parser.add_argument('-sims', type=int, required=True, help='Number of simulations to run')
    parser.add_argument('-verbose', type=bool, required=False, help='Number of simulations to run')


    args = parser.parse_args()



    # Run the simulation
    results = run_simulation_many_times(number=args.sims, verbose=args.verbose)

    # Print results
    print("Simulation Results:")
    print(results)

if __name__ == "__main__":
    main()