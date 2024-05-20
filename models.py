from pydantic import BaseModel
from typing import List

class Admin(BaseModel):
    password: str
    
class Team(BaseModel):
    team_name: str
    password: str

class Answer(BaseModel):
    code: str

