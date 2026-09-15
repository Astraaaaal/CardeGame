"""
Réglages globaux du jeu, éditables depuis l'admin — une seule ligne
(id=1), sur le même principe que les autres barèmes (niveaux, rareté...).
Remplace les anciennes variables d'environnement DAILY_BASE_REWARD /
DAILY_STREAK_BONUS : ce sont des valeurs de gameplay, pas de la config
serveur — elles n'ont pas leur place dans .env, éditable seulement via
redéploiement.
"""

from sqlmodel import SQLModel, Field


class GameConfig(SQLModel, table=True):
    __tablename__ = "game_config"

    id: int = Field(default=1, primary_key=True)
    daily_base_reward: int = Field(default=500)
    daily_streak_bonus: int = Field(default=100)
