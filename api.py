from fastapi import FastAPI,UploadFile, Request, HTTPException, status, File, Query, Depends,Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
import inspect
import logging
from game_simulation import GameSimulation
import sqlite3
from datetime import datetime, timedelta
from check_file import is_safe

import json
import os
import asyncio


from config import CURRENT_DB,CURRENT_DIR,SECRET_KEY,ADMIN_PASSWORD,ACCESS_TOKEN_EXPIRE_MINUTES
from models import Team,Admin,Answer
from auth import create_access_token,get_current_user,get_password_hash,verify_password
from database import create_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    with open(os.path.join(CURRENT_DIR, "initial.json"), 'r') as f:
        initial_data = json.load(f)
    teams_json_path = os.path.join(CURRENT_DIR, "teams.json")
    create_database(initial_data, teams_json_path)
    yield


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




def update_or_insert_timestamp(team_name):
    # Connect to the SQLite database
    conn = sqlite3.connect("teams_log.db")
    cursor = conn.cursor()

    # Get the current time
    current_time = datetime.now()

    try:
        # Try to retrieve the timestamp for the given team name
        cursor.execute("SELECT timestamp FROM teams_submission WHERE name = ?", (team_name,))
        result = cursor.fetchone()

        # If the team name is found in the database
        if result:
            # Parse the timestamp from the database
            last_timestamp = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')

            # Calculate the time difference
            time_difference = current_time - last_timestamp

            # If the difference is more than 1 minute, update the timestamp
            if time_difference > timedelta(minutes=1):
                cursor.execute("UPDATE teams_submission SET timestamp = ? WHERE name = ?", (current_time.strftime('%Y-%m-%d %H:%M:%S'), team_name))
                conn.commit()
                return True
            else:
                return False
        else:
            # If the team name is not found, insert a new record
            cursor.execute("INSERT INTO teams_submission (name, timestamp) VALUES (?, ?)", (team_name, current_time.strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            return True

        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()


@app.get("/")
async def root():
    return {"message": "Success, server is running"}


@app.post("/agent_login")
async def team_login(user: Team):
    try:
        result = execute_db_query("SELECT password FROM teams WHERE name=?",(user.team_name,),fetchone=True)
        if result is not None:
            hashed_password = result[0]
            if verify_password(user.password, hashed_password):
                print("Password verified.")
                access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                access_token = create_access_token(
                    data={"sub": user.team_name, "role": "student"}, 
                    expires_delta=access_token_expires
                )
                return {"access_token": access_token, "token_type": "bearer"}
        else:
            return {"status": "failed", "message": "No team found with these credentials"}
            
    except Exception as e:
         return {"status": "failed", "message": "Server error"}

@app.post("/submit_agent")
async def submit_agent(data: Answer, team_name: str = Depends(get_current_user)):
    try:
        #outcome = update_or_insert_timestamp(team_name)
        #if outcome:
            # Wait for 2 seconds for the processing_logic to complete
        #    result = await asyncio.wait_for(run_game(data), timeout=3)
            #if the players points are 0
        #    if "game_result" in result:
        #        if result["game_result"][team_name] == 0:
        #            return {"WARNING:":"Validated Agent is weak Score = 0"}
        #    return result
        #else:
        #    return {"error": "Your agent has been sent multiple times in one minute"}
        return {"status" : "success", "message" : "It went through"}
    except asyncio.TimeoutError:
        # Logic didn't complete in 2 seconds
        return {"error": "Your agent might be stuck in an infinite loop. It took more than 3 seconds to sim 10 games"}





if __name__=="__main__":
    create_database()
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=8000)