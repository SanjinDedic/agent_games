from fastapi import FastAPI, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from docker_simulation import run_docker_simulation, DOCKER_TIMEOUT
from validation import is_agent_safe, run_validation_simulation
from games.game_factory import GameFactory
import os
from config import ROOT_DIR
from contextlib import asynccontextmanager
from utils import transform_result, get_games_names
from auth import get_current_user, decode_id
import database
from models_api import (
    ResponseModel,
    ErrorResponseModel,
    LeagueSignUp,
    TeamSignup,
    AdminLogin,
    TeamLogin,
    SubmissionCode,
    SimulationConfig,
    LeagueAssignRequest,
    TeamDelete,
    ExpiryDate,
    LeagueName,
    LeagueResults,
    GameName
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    engine = database.get_db_engine()
    print(f"Database URL: {engine.url}")  # Add this line
    with Session(engine) as session:
        yield session

@app.get("/", response_model=ResponseModel)
async def root():
    return ResponseModel(status="success", message="Server is up and running (deploy.yml works1)")


@app.post("/league_create", response_model=ResponseModel)
async def league_create(league: LeagueSignUp, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    if not league.name:
        return ResponseModel(status="failed", message="Name is Empty")
    #if not role == "admin" then return error
    if current_user["role"] != "admin":
        return ResponseModel(status="failed", message="Unauthorized")

    league_folder = f"leagues/admin/{league.name}"

    try:
        data = database.create_league(session=session, league_name=league.name, league_game=league.game, league_folder=league_folder)
        return ResponseModel(status="success", message="League created successfully", data=data)
    except Exception as e:
        return ResponseModel(status="failed", message=str(e))


@app.post("/admin_login")
def admin_login(login: AdminLogin, session: Session = Depends(get_db)):
    try:
        print("calling get_admin with" + login.username + " " + login.password)
        token = database.get_admin_token(session, login.username, login.password)
        return ResponseModel(status="success", message="Login successful", data=token)
    except Exception as e:
        return ResponseModel(status="failed", message=str(e))


@app.post("/team_login", response_model=ResponseModel)
def team_login(credentials: TeamLogin, session: Session = Depends(get_db)):
    try:
        team_token = database.get_team_token(session, credentials.name, credentials.password)
        if team_token:
            return ResponseModel(status="success", message="Login successful", data=team_token)
    except Exception as e:
        return ResponseModel(status="failed", message=str(e))

@app.post("/team_create", response_model=ResponseModel)
async def agent_create(user: TeamSignup, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    if current_user["role"] != "admin":
        return ResponseModel(status="failed", message="Only admin users can create teams")
    try:
        data = database.create_team(session=session, name=user.name, password=user.password, school=user.school_name)
        return ResponseModel(status="success", message="Team created successfully", data=data)
    except Exception as e:
        return ResponseModel(status="failed", message=f"Server error: {str(e)}")


@app.post("/submit_agent", response_model=ResponseModel)
async def submit_agent(submission: SubmissionCode, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    team_name = current_user["team_name"]
    if not is_agent_safe(submission.code):
        return ErrorResponseModel(status="error", message="Agent code is not safe.")

    team = database.get_team(session, team_name)
    if not team.league:
        return ErrorResponseModel(status="error", message="Team is not assigned to a league.")

    if team.league.name == "unassigned":
        return ErrorResponseModel(status="error", message="Team is not assigned to a valid league.")

    try:
        if team.league.folder:
            league_folder = team.league.folder.lstrip('/')
        else:
            league_folder = f"leagues/user/{team.league.name}"

        # Check if the team can make a submission
        if not database.allow_submission(session, team.id):
            return ErrorResponseModel(status="error", message="You can only make 3 submissions per minute.")

        # Save the submitted code in a Python file named after the team
        file_path = os.path.join(ROOT_DIR, "games", team.league.game, league_folder, f"{team_name}.py")
        with open(file_path, "w") as file:
            file.write(submission.code)

        feedback, results = run_validation_simulation(submission.code, team.league.game, team_name)
        # Log the submission in the database
        submission_id = database.save_submission(session, submission.code, team.id)
        return ResponseModel(
            status="success",
            message=f"Code submitted successfully. Submission ID: {submission_id}",
            data={"results": results, "team_name": team_name, "feedback": feedback}
        )
    except Exception as e:
        return ErrorResponseModel(status="error", message=f"An error occurred while updating submission: {str(e)}")


@app.post("/run_simulation", response_model=ResponseModel)
def run_simulation(simulation_config: SimulationConfig, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    if current_user["role"] != "admin":
        return ErrorResponseModel(status="error", message="Only admin users can run simulations")

    league_name = simulation_config.league_name
    num_simulations = simulation_config.num_simulations
    custom_rewards = simulation_config.custom_rewards
    use_docker = simulation_config.use_docker if hasattr(simulation_config, 'use_docker') else True

    try:
        league = database.get_league(session, league_name)
        if not league:
            return ErrorResponseModel(status="error", message=f"League '{league_name}' not found")

        if use_docker:
            print("Running simulation using Docker")
            is_successful, results = run_docker_simulation(league_name, league.game, league.folder, custom_rewards, player_feedback=True, num_simulations=num_simulations)
            if not is_successful:
                return ErrorResponseModel(status="error", message=results)
            simulation_results = results['simulation_results']
        else:
            print("Running simulation without Docker")
            game_class = GameFactory.get_game_class(league.game)
            simulation_results = game_class.run_simulations(num_simulations, league, custom_rewards)

        if league_name != "test_league":
            sim_result = database.save_simulation_results(session, league.id, simulation_results, custom_rewards)

        response_data = transform_result(simulation_results, sim_result, league_name) 
        if use_docker:
            response_data['feedback'] = results['feedback']
        
        return ResponseModel(status="success", message="Simulation run successfully", data=response_data)

    except Exception as e:
        print(f"Error running simulation: {str(e)}")
        return ErrorResponseModel(status="error", message=f"An error occurred while running the simulation: {str(e)}")


@app.get("/get_all_admin_leagues", response_model=ResponseModel)
def get_all_admin_leagues(session: Session = Depends(get_db)):
    try:
        leagues = database.get_all_admin_leagues(session)
        return ResponseModel(status="success", message="Admin leagues retrieved successfully", data=leagues)
    except Exception as e:
        print(f"Error retrieving admin leagues: {str(e)}")
        return ErrorResponseModel(status="error", message="An error occurred while retrieving admin leagues")
    

@app.post("/league_assign", response_model=ResponseModel)
async def assign_team_to_league(league: LeagueAssignRequest, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    team_name = current_user["team_name"]
    print("team_name", team_name, "about to assign to league", league.name)
    
    if current_user["role"] not in ["admin", "student"]:
        return ErrorResponseModel(status="error", message="Only admin and student users can assign teams to leagues")
    
    try:
        msg = database.assign_team_to_league(session, team_name, league.name)
        return ResponseModel(status="success", message=msg)
    except Exception as e:
        print(f"Error assigning team to league: {str(e)}")
        return ErrorResponseModel(status="error", message="An error occurred while assigning team to league"+str(e))


@app.post("/delete_team", response_model=ResponseModel)
async def delete_team(team: TeamDelete, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    if current_user["role"] != "admin":
        return ErrorResponseModel(status="error", message="Only admin users can delete teams")
    
    try:
        msg= database.delete_team(session, team.name)
        return ResponseModel(status="success", message=msg)
    except Exception as e:
        return ErrorResponseModel(status="error", message="An error occurred while deleting the team "+str(e))


@app.get("/get_all_teams", response_model=ResponseModel)
def get_all_teams(session: Session = Depends(get_db)):
    try:
        teams = database.get_all_teams(session)
        return ResponseModel(status="success", message="Teams retrieved successfully", data=teams)
    except Exception as e:
        print(f"Error retrieving teams: {str(e)}")
        return ErrorResponseModel(status="error", message="An error occurred while retrieving teams")

@app.post("/get_all_league_results", response_model=ResponseModel)
def get_all_league_results(league: LeagueName, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    if current_user["role"] != "admin":
        return ErrorResponseModel(status="error", message="Only admin users can view league results")
    
    try:
        league_results = database.get_all_league_results(session, league.name)
        return ResponseModel(status="success", message="League results retrieved successfully", data=league_results)
    except Exception as e:
        return ErrorResponseModel(status="error", message="An error occurred while retrieving league results "+str(e))


@app.post("/publish_results", response_model=ResponseModel)
def publish_results(sim: LeagueResults, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    if current_user["role"] != "admin":
        return ErrorResponseModel(status="error", message="Only admin users can publish league results") 
    try:
        msg,data = database.publish_sim_results(session, sim.league_name, sim.id)
        return ResponseModel(status="success", message=msg, data=data)
    except Exception as e:
        return ErrorResponseModel(status="error", message="An error occurred while publishing results "+str(e))


@app.post("/get_published_results_for_league", response_model=ResponseModel)
def get_published_results_for_league(league: LeagueName, session: Session = Depends(get_db)):
    try:
        published_results = database.get_published_result(session, league.name)
        if published_results:
            return ResponseModel(status="success", message="Published results retrieved successfully", data=published_results)
        else:
            return ResponseModel(status="success", message="No published results found for the specified league", data=None)
    except Exception as e:
        return ErrorResponseModel(status="error", message="An error occurred while retrieving published results " + str(e))


@app.get("/get_published_results_for_all_leagues", response_model=ResponseModel)
def get_published_results_for_all_leagues(session: Session = Depends(get_db)):
    try:
        published_results = database.get_all_published_results(session)
        if published_results:
            return ResponseModel(status="success", message="Published results retrieved successfully", data=published_results)
        else:
            return ResponseModel(status="success", message="No published results found for the specified league", data=None)
    except Exception as e:
        print(f"Error retrieving published results: {str(e)}")
        return ErrorResponseModel(status="error", message="An error occurred while retrieving published results " + str(e))


@app.post("/update_expiry_date")
def update_expiry_date(expiry_date: ExpiryDate, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    if current_user["role"] != "admin":
        return ResponseModel(status="failed", message="Only admin users can update the expiry date")
    try:
        message = database.update_expiry_date(session, expiry_date.league, expiry_date.date)
        if "not found" in message:
            return ErrorResponseModel(status="failed", message = message)
        return ResponseModel(status="success", message = message)
    except Exception as e:
        ErrorResponseModel(status="error", message= str(e))


@app.post("/get_game_instructions", response_model=ResponseModel)
async def get_game_instructions(game: GameName):
    try:
        game_class = GameFactory.get_game_class(game.game_name)
        return ResponseModel(
            status="success",
            message="Game instructions retrieved successfully",
            data={
                "starter_code": game_class.starter_code,
                "game_instructions": game_class.game_instructions
            }
        )
    except Exception as e:
        return ErrorResponseModel(status="error", message=f"An error occurred: {str(e)}")
    

@app.post("/get_available_games", response_model=ResponseModel)
async def get_available_game():
    try:
        game_names = get_games_names()
        
        return ResponseModel(
            status="success",
            message="Available games retrieved successfully",
            data={ "games" :game_names }
        )
    except Exception as e:
        return ErrorResponseModel(status="error", message=f"An error occurred: {str(e)}")