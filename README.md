# 🎮 Multi-Game Simulation Platform
![Python](https://img.shields.io/badge/python-3.12-blue.svg)  [![Tests](https://github.com/SanjinDedic/agent_games/actions/workflows/test.yml/badge.svg)](https://github.com/SanjinDedic/agent_games/actions/workflows/test.yml)  [![codecov](https://codecov.io/gh/SanjinDedic/agent_games/graph/badge.svg?token=PWUU4GJSOD)](https://codecov.io/gh/SanjinDedic/agent_games)

## 🌟 Overview
The Multi-Game Simulation Platform is a Python-based project that allows users to simulate and play various games, starting with the popular dice game, Greedy Pig. The platform has been expanded to support multiple games and includes a front-end interface for enhanced user experience.

## 🚀 Getting Started
To get started with the Multi-Game Simulation Platform, follow these steps:

1. Clone the repository: `git clone https://github.com/your-username/multi-game-simulation.git`
2. Install the required dependencies: `pip install -r requirements.txt`
3. Set up the database by running the database initialization script: `python initialize_db.py`
4. Start the FastAPI server: `uvicorn api:app --reload`
5. Access the platform through the provided front-end interface.

## 🎲 Greedy Pig Game
Greedy Pig is the first game implemented on the platform. It's a simple dice game with interesting and unpredictable dynamics when played by a large number of players. The game's optimal play has been a subject of many academic papers and discussions. More information can be found here:

- [The Statistical Problem of Greedy Pigs](https://www.smh.com.au/education/the-statistical-problem-of-greedy-pigs-20140728-3cpk8.html)
- [Optimal Play of the Dice Game "Pig"](https://cupola.gettysburg.edu/cgi/viewcontent.cgi?article=1003&context=csfac)

## 🏗️ Project Structure
The project is structured as follows:

- `api.py`: The main FastAPI application file that handles API endpoints and request handling.
- `auth.py`: Contains authentication-related functions and utilities.
- `config.py`: Stores configuration variables and settings for the project.
- `database.py`: Handles database operations and interactions.
- `models.py`: Defines the database models and schemas used in the project.
- `games/`: A directory that contains game-specific files and implementations.
  - `greedy_pig/`: The Greedy Pig game implementation.
    - `greedy_pig.py`: The main game logic for Greedy Pig.
    - `greedy_pig_sim.py`: Simulation and animation functions for Greedy Pig.
    - `leagues/`: A directory that stores league-specific files and player implementations.
- `validation.py`: Contains validation functions for agent code and simulations.
- `requirements.txt`: Lists the project dependencies.

## 🌐 API Endpoints
The following API endpoints are available:

- `/`: Root endpoint for testing server status.
- `/league_create`: Creates a new league.
- `/league_join/{link}`: Allows users to join a league using a specific link.
- `/team_login`: Handles team login and authentication.
- `/team_create`: Creates a new team (admin only).
- `/submit_agent`: Submits an agent code for a specific team.
- `/admin_login`: Handles admin login and authentication.
- `/run_simulation`: Runs a simulation for a specific league (admin only).
- `/get_all_admin_leagues`: Retrieves all admin leagues.
- `/league_assign`: Assigns a team to a league.
- `/delete_team`: Deletes a team (admin only).
- `/toggle_league_active`: Toggles the active status of a league (admin only).
- `/get_all_teams`: Retrieves all teams.
- `/get_all_league_results`: Retrieves results for a specific league (admin only).

## 🔒 Security Features
The platform includes the following security features:

- Authentication and authorization using JSON Web Tokens (JWT).
- Password hashing using the `bcrypt` algorithm.
- Input validation and sanitization to prevent script injection and unauthorized access.
- CORS (Cross-Origin Resource Sharing) middleware for secure cross-origin requests.

## 🌐 Front-end Interface
The platform includes a user-friendly front-end interface built with modern web technologies. The front-end communicates with the FastAPI backend through API requests and provides an intuitive way for users to interact with the platform, create and join leagues, submit agents, and view simulation results.

## 🔧 Customization and Expansion
The Multi-Game Simulation Platform is designed to be easily customizable and expandable. You can add new games by following these steps:

1. Create a new directory for the game inside the `games/` directory.
2. Implement the game logic and simulation functions in separate Python files.
3. Define the necessary API endpoints and request handlers in `api.py`.
4. Update the front-end interface to include the new game and its features.

## 🤝 Contributing
Contributions to the Multi-Game Simulation Platform are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request on the project's GitHub repository.


## 📄 License
This work is licensed under a [Creative Commons Attribution-NonCommercial 4.0 International License](http://creativecommons.org/licenses/by-nc/4.0/).

You are free to:
- Share — copy and redistribute the material in any medium or format
- Adapt — remix, transform, and build upon the material

Under the following terms:
- Attribution — You must give appropriate credit, provide a link to the license, and indicate if changes were made. You may do so in any reasonable manner, but not in any way that suggests the licensor endorses you or your use.
- NonCommercial — You may not use the material for commercial purposes.

No additional restrictions — You may not apply legal terms or technological measures that legally restrict others from doing anything the license permits.

Notices:
- You do not have to comply with the license for elements of the material in the public domain or where your use is permitted by an applicable exception or limitation.
- No warranties are given. The license may not give you all of the permissions necessary for your intended use. For example, other rights such as publicity, privacy, or moral rights may limit how you use the material.

For more information, please see the full text of the [CC BY-NC 4.0 license](https://creativecommons.org/licenses/by-nc/4.0/legalcode).

Make sure to include a link to the full text of the CC BY-NC 4.0 license, as provided above. You can also include a separate `LICENSE` file in your project repository containing the complete license text.

Please note that while this license allows for non-commercial use, sharing, and adaptation of your work, it does not explicitly grant permissions for educational institutions. If you want to specifically allow educational use, you may consider using the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0) license instead, which includes provisions for educational purposes.
