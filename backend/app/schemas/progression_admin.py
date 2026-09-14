"""
Schemas — édition admin des barèmes de progression (niveaux, achievements,
quêtes). Champs "tunables" uniquement (pas de création/suppression pour
l'instant, la liste est fixée au seed — cf. app/migrations.py).
"""

from pydantic import BaseModel


class LevelTierPatch(BaseModel):
    power_required: int | None = None
    reward_resource_id: str | None = None
    reward_amount: int | None = None


class AchievementDefPatch(BaseModel):
    threshold: int | None = None
    reward_resource_id: str | None = None
    reward_amount: int | None = None
    reward_booster_id: str | None = None
    active: bool | None = None


class QuestDefPatch(BaseModel):
    threshold: int | None = None
    reward_resource_id: str | None = None
    reward_amount: int | None = None
    active: bool | None = None
