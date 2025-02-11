from typing import List, Optional

from pydantic import BaseModel, field_validator


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

    # ensure that the number of simulations is between 1 and 1000
    @field_validator("num_simulations")
    def check_num_simulations(cls, v):
        if not 1 <= v <= 1000:
            raise ValueError("Number of simulations must be between 1 and 1000")
        return v
