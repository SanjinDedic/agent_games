# 🐷 Greedy Pig Game Simulation Project

## 🌟 Overview
The Greedy Pig Game Simulation is a Python-based project that simulates the popular dice game, Greedy Pig. It's a simple dice game with very interesting and unpredictable dynamics when played by a large number of players. This primary school game's optimal play has been a subject of many academic papers and discussions. More information can be found here:

- [The Statistical Problem of Greedy Pigs](https://www.smh.com.au/education/the-statistical-problem-of-greedy-pigs-20140728-3cpk8.html)
- [Optimal Play of the Dice Game "Pig"](https://cupola.gettysburg.edu/cgi/viewcontent.cgi?article=1003&context=csfac)

## 🚀 Getting Started
The simplest way to play:
- Use `single_file_game`.
- Modify one or more of the players.
- Modify the `assign_points()` function.

👥 To play with friends or against other people:
- Fork this repl: [agentSIMX](https://replit.com/@SanjinDedic/agentSIMX).
- Use Replit in multiplayer mode. This allows each player to edit an agent and run a simulation.

## 🏠 How to Host a Game
To host the Greedy Pig Game Simulation, you will need:
- A Linux server (nginx or Apache2).
- Run `python3 api.py` to start the FastAPI application.
- For 24/7 agent reception, configure `systemd` to manage the FastAPI app as a service.
- Ensure all agents are located in the `classes` folder.
- Create credentials for each participant by modifying `teams.json`
- Provide each player with credentials and a link to the `agent_send.py` script from this repo to send their agents
- To run a simulation:
  ```bash
  python3 live_table.py -sims 20000 -refresh 500
  ```

## 📚 Project Structure

### `player_base.py`

This file defines the `Player` class, which serves as the base class for all agents in the game. Key aspects include:

- **Initialization**: The `Player` class is initialized with a name, password, and default values for `banked_money`, `unbanked_money`, and `has_banked_this_turn`. 
- **Money Management**: Methods like `reset_unbanked_money()` and `bank_money()` manage the player's in-game finances.
- **Abstract Methods**: Being an abstract base class (ABC), it requires derived classes to implement specific methods, such as making game decisions.

### `multi_player_game.py`

Manages the game environment, including classes and functions for game mechanics. Key components:

- **`Dice` Class**: Provides a simple dice rolling functionality.
  - **`roll` Method**: Generates a random number between 1 and 6, simulating a dice roll.

- **`Game` Class**: Central class for managing game flow and interactions.
  - **`get_game_state` Method**: Retrieves the current state of the game. 
  - **`play_round` Method**: Handles the logic for playing a single round in the game. 
  - **`play_game` Method**: Manages the overall game play, including looping through rounds. 

- **Functions**:
  - **`run_simulation_many_times`**: Runs the game simulation multiple times, with parameters for the number of simulations, verbosity, and class file location.
  - **`assign_points`**: Assigns points to players based on game results, with an optional maximum score parameter.
  - **`get_all_player_classes_from_folder`**: Retrieves all player class definitions from a specified folder, aiding in dynamic player class integration.

### `agent_send.py`

This script deals with sending the agent to the server for participation in the game. It includes:

- **HTTP Request**: Sends the agent's code to the server using an HTTP POST request. The request requires credentials (`team_name` and `password`).
- **Server Response**: The server's response indicates whether the agent is accepted and validated. It also provides feedback on the agent's performance.

### `animate_multi_player_game.py`

- This file extends the functionality of `multi_player_game.py` by adding animation
- It features an interactive simulation table using the `rich` Python module.
- There's planned integration with `multi_player_game.py` because current structure has redundancies
- The script includes a formatted table printout with colors to enhance readability and user engagement. This is achieved using the `Table` class from the `rich.table` module. The table dynamically updates during the game, showing player positions, scores, and other relevant information in a visually appealing manner.

### `live_table.py`

- Utilizes command-line arguments for simulation customization, including number of simulations, refresh rate, and player class folder.
- Integrates with `animated_multi_player_game` for animated game simulations.

To run the script, use the following command in the terminal:

```bash
python3 live_table.py -sims 20000 -refresh 500 -folder classes-by-strategy
```

- `-sims 20000`: Specifies the number of game simulations to run. In this example, it will run 20,000 simulations.
- `-refresh 500`: Sets the refresh rate for the animation in milliseconds. Here, it's set to 500 milliseconds.
- `-folder classes-by-strategy`: Indicates the folder where the player class files are located. This allows the script to access different player strategies for the simulations.


## 🖥️ api.py
Serves as the backbone for agent validation and game management. Includes:

### Endpoints
- **Agent Upload**: For uploading agent files.
- **Simulation Trigger**: To start a simulation.
- **Status Check**: For current game status.

### Validation of Agents
Includes checks for script injection prevention, file system access control, and game logic adherence.

### Security Features
- **Rate Limiting**: To prevent API abuse.
- **CORS Middleware**: For secure cross-origin requests.
- **Error Handling**: For clear feedback and preventing sensitive information leakage.

## 📁 Repository Structure

```sh
└── agent_games/
    ├── agent_send.py
    ├── animated_multi_player_game.py
    ├── api.py
    ├── colors.json
    ├── live_table.py
    ├── multi_player_game.py
    ├── player_base.py
    ├── single_file_game.py
    ├── stress_tests/
    │   └── stress_test.py
    ├── teams.json
    ├── classes/
    │   └── .nothing
    ├── classes-by-strategy/
    │   ├── AI_Agent.py
    │   ├── . . 11 more player classes
    ├── test_classes/
    │   ├── AlwaysBank.py
    │   ├── . . 8 more player classes
    └── vcc_classes/
        ├── .nothing
        ├── AlwaysBank.py
        ├── . . 16 more player classes
```
