"""
Achievements — objectifs permanents évalués à la demande (pas de suivi
d'événements en temps réel : on recalcule la métrique concernée quand le
joueur consulte sa page achievements, on débloque si le seuil est atteint).
"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

# Métriques supportées par app/services/achievements.py :
# total_cards, packs_opened, trades_completed, friends_count, gifts_sent,
# cards_recycled, coins_balance, login_streak, level, types_owned_distinct,
# type_complete, rarity_owned (metric_param = id de rareté), jewelry_owned
# (metric_param), specialty_owned (metric_param), card_power, combined_rarity,
# meta_unlocked_ratio
ACHIEVEMENT_METRICS = (
    "total_cards", "packs_opened", "trades_completed", "friends_count", "gifts_sent", "cards_recycled",
    "coins_balance", "login_streak", "level", "types_owned_distinct", "type_complete",
    "rarity_owned", "jewelry_owned", "specialty_owned", "card_power", "combined_rarity",
    "meta_unlocked_ratio",
)


class AchievementDef(SQLModel, table=True):
    __tablename__ = "achievement_defs"

    id: str = Field(primary_key=True, max_length=50)
    name: str = Field(max_length=100)
    description: str = Field(default="")
    category: str = Field(max_length=20)  # collection | social | economy | progression | meta
    metric: str = Field(max_length=30)
    threshold: int = Field(default=1)
    # Paramètre additionnel pour les métriques qui en ont besoin (ex: rarity_owned -> "legendary").
    metric_param: Optional[str] = Field(default=None, max_length=30)

    reward_resource_id: Optional[str] = Field(default=None, foreign_key="resources.id", max_length=30)
    reward_amount: Optional[int] = Field(default=None)
    reward_booster_id: Optional[str] = Field(default=None, foreign_key="boosters.id", max_length=30)

    active: bool = Field(default=True)


class UserAchievement(SQLModel, table=True):
    """Débloqué (+ éventuellement récupéré) pour un joueur donné."""
    __tablename__ = "user_achievements"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    achievement_id: str = Field(foreign_key="achievement_defs.id", primary_key=True, max_length=50)
    unlocked_at: datetime = Field(default_factory=datetime.utcnow)
    claimed_at: Optional[datetime] = Field(default=None)
