"""
Schemas — niveaux, achievements, quêtes.
"""

from datetime import datetime
from pydantic import BaseModel


class PendingLevelReward(BaseModel):
    level: int
    reward_resource_id: str | None = None
    reward_amount: int | None = None
    reward_booster_id: str | None = None
    reward_booster_name: str | None = None


class LevelStatus(BaseModel):
    current_level: int
    total_power: int
    claimed_level: int
    next_level_power_required: int | None = None
    pending_rewards: list[PendingLevelReward] = []
    has_unclaimed: bool = False


class LevelTierOut(BaseModel):
    """Un palier de la table complète — pour la "route" affichant tous les
    niveaux avec leurs récompenses (cf. Progression.tsx)."""
    level: int
    power_required: int
    reward_resource_id: str | None = None
    reward_resource_name: str | None = None
    reward_amount: int | None = None
    reward_booster_id: str | None = None
    reward_booster_name: str | None = None
    reached: bool = False
    claimed: bool = False


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
