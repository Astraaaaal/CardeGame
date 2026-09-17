"""
Quêtes journalières/hebdomadaires — rotation de quelques quêtes tirées au
hasard parmi les modèles actifs, assignées pour la période en cours, avec
une progression qui se remet à zéro à chaque nouvelle période (contrairement
aux achievements qui sont permanents).
"""

from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

# Mêmes métriques que les quêtes savent suivre (cf. app/services/quest_progress.py) :
# packs_opened, trades_completed, gifts_sent, cards_recycled, friend_requests_sent,
# shop_purchases, rerolls_used, rare_cards_obtained, legendary_cards_obtained, daily_rewards_claimed
QUEST_METRICS = (
    "packs_opened", "trades_completed", "gifts_sent", "cards_recycled", "friend_requests_sent",
    "shop_purchases", "rerolls_used", "rare_cards_obtained", "legendary_cards_obtained", "daily_rewards_claimed",
)

DAILY_QUEST_COUNT = 3
WEEKLY_QUEST_COUNT = 2


class QuestDef(SQLModel, table=True):
    __tablename__ = "quest_defs"

    id: str = Field(primary_key=True, max_length=50)
    name: str = Field(max_length=100)
    description: str = Field(default="")
    period: str = Field(max_length=10)  # "daily" | "weekly"
    metric: str = Field(max_length=30)
    threshold: int = Field(default=1)

    reward_resource_id: Optional[str] = Field(default=None, foreign_key="resources.id", max_length=30)
    reward_amount: Optional[int] = Field(default=None)
    # Un booster non ouvert, en plus ou à la place d'une récompense en
    # ressource (crédité à l'inventaire, cf. app/models/booster_inventory.py).
    reward_booster_id: Optional[str] = Field(default=None, foreign_key="boosters.id", max_length=30)

    active: bool = Field(default=True)


class QuestProgress(SQLModel, table=True):
    """Compteur d'un métrique pour un joueur, sur UNE période précise
    (period_key = "2026-09-14" en daily, "2026-W37" en weekly) — se remet
    naturellement à zéro puisqu'une nouvelle période a une nouvelle clé."""
    __tablename__ = "quest_progress"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    metric: str = Field(primary_key=True, max_length=30)
    period: str = Field(primary_key=True, max_length=10)
    period_key: str = Field(primary_key=True, max_length=20)
    count: int = Field(default=0)


class UserQuest(SQLModel, table=True):
    """Une quête assignée à un joueur pour une période précise (tirée au
    hasard parmi les QuestDef actifs de cette période lors du premier accès)."""
    __tablename__ = "user_quests"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    quest_def_id: str = Field(foreign_key="quest_defs.id", max_length=50)
    period: str = Field(max_length=10)
    period_key: str = Field(max_length=20)
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    claimed_at: Optional[datetime] = Field(default=None)
