from fastapi import FastAPI, HTTPException, status, File, Query, Depends, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import create_engine, select, Session
from validation import is_agent_safe, run_agent_simulation
from games.game_factory import GameFactory
import asyncio
import os
from config import get_database_url, ACCESS_TOKEN_EXPIRE_MINUTES, ROOT_DIR
from contextlib import asynccontextmanager
from models_db import *
from models_api import *
from utils import transform_result
from auth import get_current_user, create_access_token, decode_id
from database import *



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
    engine = get_db_engine()
    print(f"Database URL: {engine.url}")  # Add this line
    with Session(engine) as session:
        yield session

@app.get("/", response_model=ResponseModel)
async def root():
    return ResponseModel(status="success", message="Server is up and running (deploy.yml works1)")


@app.post("/league_create", response_model=ResponseModel)
async def league_create(league: LeagueSignUp, authorization: str = Header(None), session: Session = Depends(get_db)):
    if not league.name:
        return ResponseModel(status="failed", message="Name is Empty")

    user_role = "user"
    if authorization and authorization.startswith("Bearer "):
        user = get_current_user(authorization.split(" ")[1])
        if user["role"] == "admin":
            user_role = "admin"

    if user_role == "admin":
        league_folder = f"/leagues/admin/{league.name}"
    else:
        league_folder = f"/leagues/user/{league.name}"

    try:
        data = create_league(session=session, league_name=league.name, league_game=league.game, league_folder=league_folder)
        return ResponseModel(status="success", message="League created successfully", data=data)
    except Exception as e:
        return ResponseModel(status="failed", message=str(e))

@app.post("/league_join/{link}") #rename to user_league_join
async def league_join(link, user: TeamSignUp, session: Session = Depends(get_db)):
    #ths will only apply to user created leagues
    #find league_id from link
    try:
        league_id = decode_id(link)
        user_data = TeamSignUp.model_validate(user)
        print(user_data)
        return create_team(session=session, name=user.name, password=user.password, league_id=league_id, school=user.school)
    except Exception as e:
        return {"status": "failed", "message": "Server error"}

@app.post("/admin_login")
def admin_login(login: AdminLogin, session: Session = Depends(get_db)):
    try:
        print("calling get_admin with" + login.username + " " + login.password)
        token = get_admin_token(session, login.username, login.password)
        return ResponseModel(status="success", message="Login successful", data=token)
    except Exception as e:
        return ResponseModel(status="failed", message=str(e))


@app.post("/team_login", response_model=ResponseModel)
def team_login(credentials: TeamLogin, session: Session = Depends(get_db)):
    try:
        team_token = get_team_token(session, credentials.name, credentials.password)
        if team_token:
            return ResponseModel(status="success", message="Login successful", data=team_token)
    except Exception as e:
        return ResponseModel(status="failed", message=str(e))

@app.post("/team_create", response_model=ResponseModel)
async def agent_create(user: TeamSignup, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    if current_user["role"] != "admin":
        return ResponseModel(status="failed", message="Only admin users can create teams")
    try:
        data = create_team(session=session, name=user.name, password=user.password, school=user.school_name)
        return ResponseModel(status="success", message="Team created successfully", data=data)
    except Exception as e:
        return ResponseModel(status="failed", message=f"Server error: {str(e)}")


@app.post("/submit_agent", response_model=ResponseModel)
async def submit_agent(submission: SubmissionCode, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    team_name = current_user["team_name"]
    user_role = current_user["role"]
    if not is_agent_safe(submission.code):
        return ErrorResponseModel(status="error", message="Agent code is not safe.")
    
    team = get_team(session, team_name)
    if not team.league:
        return ErrorResponseModel(status="error", message="Team is not assigned to a league.")
    
    results = run_agent_simulation(submission.code, team.league.game, team_name)
    if not results:
        return ErrorResponseModel(status="error", message="Agent simulation failed.")
    
    try:
        print("team found", team.name, team.league.name, team.league.folder)
        if team.league.folder:
            league_folder = team.league.folder
        else:
            league_folder = f"leagues/user/{team.league.name}"
        print(team_name, user_role, team.league.name)

        # Check if the team can make a submission
        if not allow_submission(session, team.id):
            return ErrorResponseModel(status="error", message="You can only make 3 submissions per minute.")

        # Save the submitted code in a Python file named after the team
        file_path = os.path.join(ROOT_DIR, "games", team.league.game, league_folder, f"{team_name}.py")
        with open(file_path, "w") as file:
            file.write(submission.code)
        print("are we here")
        # Log the submission in the database
        print(submission.code)
        print(team.id)
        submission_id = save_submission(session, submission.code, team.id)
        return ResponseModel(
            status="success",
            message=f"Code submitted successfully. Submission ID: {submission_id}",
            data={"results": results, "team_name": team_name}
        )
    except Exception as e:
        print(f"Error updating submission: {str(e)}")
        return ErrorResponseModel(status="error", message=f"An error occurred while updating submission: {str(e)}")


@app.post("/run_simulation", response_model=ResponseModel)
def run_simulation(simulation_config: SimulationConfig, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    if current_user["role"] != "admin":
        return ErrorResponseModel(status="error", message="Only admin users can run simulations")

    league_name = simulation_config.league_name
    num_simulations = simulation_config.num_simulations
    
    try:
        league = get_league(session, league_name)
        if not league:
            return ErrorResponseModel(status="error", message=f"League '{league_name}' not found")
        
        game_class = GameFactory.get_game_class(league.game)
        results = game_class.run_simulations(num_simulations, game_class, league)
        
        if league_name != "test_league":
            sim_id = save_simulation_results(session, league.id, results)
        
        return ResponseModel(status="success", message="Simulation run successfully", data=transform_result(results, sim_id))
    
    except Exception as e:
        print(f"Error running simulation: {str(e)}")
        return ErrorResponseModel(status="error", message="An error occurred while running the simulation")

@app.get("/get_all_admin_leagues", response_model=ResponseModel)
def get_all_admin_leagues(session: Session = Depends(get_db)):
    try:
        leagues = get_all_admin_leagues_from_db(session)
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
        msg = assign_team_to_league_in_db(session, team_name, league.name)
        return ResponseModel(status="success", message=msg)
    except Exception as e:
        print(f"Error assigning team to league: {str(e)}")
        return ErrorResponseModel(status="error", message="An error occurred while assigning team to league"+str(e))


@app.post("/delete_team", response_model=ResponseModel)
async def delete_team(team: TeamDelete, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    if current_user["role"] != "admin":
        return ErrorResponseModel(status="error", message="Only admin users can delete teams")
    
    try:
        msg= delete_team_from_db(session, team.name)
        return ResponseModel(status="success", message=msg)
    except Exception as e:
        return ErrorResponseModel(status="error", message="An error occurred while deleting the team "+str(e))


@app.get("/get_all_teams", response_model=ResponseModel)
def get_all_teams(session: Session = Depends(get_db)):
    try:
        teams = get_all_teams_from_db(session)
        return ResponseModel(status="success", message="Teams retrieved successfully", data=teams)
    except Exception as e:
        print(f"Error retrieving teams: {str(e)}")
        return ErrorResponseModel(status="error", message="An error occurred while retrieving teams")

@app.post("/get_all_league_results", response_model=ResponseModel)
def get_all_league_results(league: LeagueName, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    if current_user["role"] != "admin":
        return ErrorResponseModel(status="error", message="Only admin users can view league results")
    
    try:
        league_results = get_all_league_results_from_db(session, league.name)
        return ResponseModel(status="success", message="League results retrieved successfully", data=league_results)
    except Exception as e:
        return ErrorResponseModel(status="error", message="An error occurred while retrieving league results "+str(e))


@app.post("/publish_results", response_model=ResponseModel)
def publish_results(sim: LeagueResults, current_user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    if current_user["role"] != "admin":
        return ErrorResponseModel(status="error", message="Only admin users can publish league results") 
    try:
        msg,data = publish_sim_results(session, sim.league_name, sim.id)
        return ResponseModel(status="success", message=msg, data=data)
    except Exception as e:
        return ErrorResponseModel(status="error", message="An error occurred while publishing results "+str(e))


@app.post("/get_published_results_for_league", response_model=ResponseModel)
def get_published_results_for_league(league: LeagueName, session: Session = Depends(get_db)):
    try:
        published_results = get_published_result(session, league.name)
        if published_results:
            return ResponseModel(status="success", message="Published results retrieved successfully", data=published_results)
        else:
            return ResponseModel(status="success", message="No published results found for the specified league", data=None)
    except Exception as e:
        return ErrorResponseModel(status="error", message="An error occurred while retrieving published results " + str(e))


@app.get("/get_published_results_for_all_leagues", response_model=ResponseModel)
def get_published_results_for_all_leagues(session: Session = Depends(get_db)):
    try:
        published_results = get_all_published_results(session)
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
        message = update_expiry_date_in_db(session, expiry_date.league, expiry_date.date)
        if "not found" in message:
            return ErrorResponseModel(status="failed", message = message)
        return ResponseModel(status="success", message = message)
    except Exception as e:
        ErrorResponseModel(status="error", message= str(e))


