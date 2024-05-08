from fastapi import FastAPI, HTTPException, status, File, Query, Depends,Body
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

from contextlib import asynccontextmanager
from config import CURRENT_DB,CURRENT_DIR,SECRET_KEY,ADMIN_PASSWORD,ACCESS_TOKEN_EXPIRE_MINUTES
from models import Team, Admin, Answer
from auth import create_access_token,get_current_user,get_password_hash,verify_password
from database import create_database,execute_db_query,update_submission
from game import Game


@asynccontextmanager
async def lifespan(app: FastAPI):
    with open(os.path.join(CURRENT_DIR, "initial.json"), 'r') as f:
        initial_data = json.load(f)
    teams_json_path = os.path.join(CURRENT_DIR, "teams.json")
    create_database(initial_data, teams_json_path)
    yield


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Success, server is up and running (deploy.yml works5)"}


@app.post("/agent_login")
async def team_login(user: Team):
    try:
        result = execute_db_query("SELECT password FROM teams WHERE name=?",(user.team_name,),fetchone=True)
        if result is not None:
            hashed_password = result[0]
            if verify_password(user.password, hashed_password):
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
async def submit_agent(data: Answer, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        if is_safe(data.code):
            
            #output = execute_code_in_docker(data.code)
            #update_submission(team_name,code)
            return {"status" : "success", "message" : "It went through"}
        else:
            return {"error": "Code is unsafe to execute"}
        
        
    except asyncio.TimeoutError:
        # Logic didn't complete in 2 seconds
        return {"error": "Your agent might be stuck in an infinite loop. It took more than 3 seconds to sim 10 games"}
    

@app.post("/admin_login")
async def admin_login(a: Admin):
    if not a.admin_password:
        return {"status": "failed", "message": "Admin credentials are wrong"}
    if a.admin_password != ADMIN_PASSWORD:
        return {"status": "failed", "message": "Admin credentials are wrong"}
    else:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": "admin", "role": "admin"}, 
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    

@app.post("/run_simulation")
async def run_simulation(number_of_runs: int, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return {"status": "success", "message": "result"}
