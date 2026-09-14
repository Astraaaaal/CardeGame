"""
Schemas — niveaux, achievements, quêtes.
"""

from datetime import datetime
from pydantic import BaseModel


class PendingLevelReward(BaseModel):
    level: int
    reward_resource_id: str | None = None
    reward_amount: int | None = None


class LevelStatus(BaseModel):
    current_level: int
    total_power: int
    claimed_level: int
    next_level_power_required: int | None = None
    pending_rewards: list[PendingLevelReward] = []
    has_unclaimed: bool = False


class AchievementOut(BaseModel):
    id: str
    name: str
    description: str
    category: str
    threshold: int
    progress: int
    reward_resource_id: str | None = None
    reward_amount: int | None = None
    reward_booster_id: str | None = None
    unlocked_at: datetime | None = None
    claimed_at: datetime | None = None


class QuestOut(BaseModel):
    id: int
    quest_def_id: str
    name: str
    description: str
    period: str
    threshold: int
    progress: int
    reward_resource_id: str | None = None
    reward_amount: int | None = None
    completed: bool
    claimed_at: datetime | None = None
