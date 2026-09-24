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
    # Type réellement affiché, quand le serveur l'a choisi lui-même.
    type_name: str | None = None
    entries: list[LeaderboardEntry] = []
