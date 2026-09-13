"""
Schemas — classements de puissance (amis, global, par type de personnage).
"""

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    username: str
    display_name: str
    total_power: int


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry] = []
