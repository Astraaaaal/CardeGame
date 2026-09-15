"""Schema — édition admin des réglages globaux du jeu (cf. app/models/game_config.py)."""

from pydantic import BaseModel


class GameConfigPatch(BaseModel):
    daily_base_reward: int | None = None
    daily_streak_bonus: int | None = None
