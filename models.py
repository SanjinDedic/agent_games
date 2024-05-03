from pydantic import BaseModel
from typing import List

class Admin(BaseModel):
    password: str
    simulations: int
    score: int
    
class Team(BaseModel):
    team_name: str
    password: str

class Answer(BaseModel):
    code: str
