"""
Distinctions : badges **accordés**, pas gagnés sur une mesure.

Les succès (app/models/achievement.py) se débloquent tout seuls quand une
métrique atteint un seuil. Une distinction, elle, est attribuée — parce qu'on
était là pendant la bêta, parce qu'on a soutenu le jeu, parce qu'on a gagné un
événement. D'où une table à part plutôt qu'un succès tordu.

Elles **survivent à la remise à zéro des comptes** : c'est tout leur intérêt.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

# Identifiants des distinctions posées par le jeu lui-même.
BETA_TESTER_ID = "beta_tester"
FOUNDER_ID = "founder"


class Distinction(SQLModel, table=True):
    """Définition d'un badge : ce qui s'affiche sur la vitrine du joueur."""
    __tablename__ = "distinctions"

    id: str = Field(primary_key=True, max_length=40)
    name: str = Field(max_length=60)
    description: str = Field(default="", max_length=200)
    # Teinte de la pastille (bordure et fond dérivés côté interface).
    color: str = Field(default="#b08d57", max_length=9)
    active: bool = Field(default=True)
    # Ordre d'affichage quand un joueur en porte plusieurs (petit = devant).
    sort_order: int = Field(default=0)
    # Survit-elle à une remise à zéro des comptes ? Vrai par défaut : oublier
    # le tag sur un badge saisonnier n'est qu'un désagrément, l'oublier sur
    # « Fondateur » effacerait ce qu'on ne peut pas reconstituer.
    keeps_on_reset: bool = Field(default=True)


class UserDistinction(SQLModel, table=True):
    """Attribution d'une distinction à un joueur. Une seule par couple."""
    __tablename__ = "user_distinctions"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    distinction_id: str = Field(foreign_key="distinctions.id", primary_key=True, max_length=40)
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    # Pourquoi elle a été donnée (trace pour l'admin : « achat du 23/09 »).
    reason: Optional[str] = Field(default=None, max_length=200)
