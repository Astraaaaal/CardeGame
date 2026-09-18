"""
Réglages globaux du jeu, éditables depuis l'admin — une seule ligne
(id=1), sur le même principe que les autres barèmes (niveaux, rareté...).
Remplace les anciennes variables d'environnement DAILY_BASE_REWARD /
DAILY_STREAK_BONUS : ce sont des valeurs de gameplay, pas de la config
serveur — elles n'ont pas leur place dans .env, éditable seulement via
redéploiement.
"""

from sqlalchemy import JSON, Column
from sqlmodel import SQLModel, Field


class GameConfig(SQLModel, table=True):
    __tablename__ = "game_config"

    id: int = Field(default=1, primary_key=True)
    daily_base_reward: int = Field(default=500)
    daily_streak_bonus: int = Field(default=100)
    # Boutique premium : fermée par défaut. Les pseudos listés (séparés par
    # des virgules) y ont accès même fermée, pour tester.
    premium_shop_enabled: bool = Field(default=False)
    premium_testers: str = Field(default="")
    # Réglages des activités (présence, expéditions, atelier, mini-jeux),
    # fusionnés avec les valeurs par défaut de app/services/activities_config.py.
    activities: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=True))
