from typing import List, Optional

from pydantic import BaseModel


class ValidationRequest(BaseModel):
    code: str
    game_name: str
    team_name: str


class SimulationRequest(BaseModel):
    league_id: int
    game_name: str
    num_simulations: int = 100
    custom_rewards: Optional[List[int]] = None
    player_feedback: bool = False
