"""
Niveaux — paliers de puissance cumulée (User.total_power, cf. leaderboard/
power.py). Table éditable depuis l'admin (comme les autres barèmes du jeu)
pour pouvoir retoucher la courbe sans redéploiement, notamment quand le
roster de personnages grossit (la puissance moyenne obtenue par carte
grimpe avec le nombre de personnages, cf. discussion de conception).
"""

from typing import Optional
from sqlmodel import SQLModel, Field


class LevelTier(SQLModel, table=True):
    __tablename__ = "level_tiers"

    level: int = Field(primary_key=True)
    power_required: int = Field(default=0)
    reward_resource_id: Optional[str] = Field(default=None, foreign_key="resources.id", max_length=30)
    reward_amount: Optional[int] = Field(default=None)
    # Optionnel, en plus (pas à la place) de la récompense en ressource —
    # crédité à l'inventaire de boosters (cf. booster_inventory.py), pas
    # ouvert directement.
    reward_booster_id: Optional[str] = Field(default=None, foreign_key="boosters.id", max_length=30)
