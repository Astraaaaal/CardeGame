"""
Cadeau de réouverture de la bêta 2.0 : les bordures d'avatar réservées aux
joueurs de la première bêta. Cinq teintes, aucune animation — une décoration
sobre, destinée à être redessinée à la main plus tard.

Le joueur n'en reçoit **qu'une**, celle qu'il choisit à la récupération du
message (cf. la récompense « cosmetic_choice » dans message_rewards.py).
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.premium import Cosmetic

logger = logging.getLogger("app")

# Identifiants stables : ils partent dans le message de cadeau.
BETA_FRAME_IDS = (
    "frame_beta_bronze",
    "frame_beta_givre",
    "frame_beta_vert_de_gris",
    "frame_beta_prune",
    "frame_beta_ambre",
)

_FRAMES = (
    {
        "id": "frame_beta_bronze", "name": "Bronze patiné",
        "description": "Bordure des joueurs de la première bêta.",
        "color_from": "#b08d57", "color_to": "#6b4a24",
    },
    {
        "id": "frame_beta_givre", "name": "Verre givré",
        "description": "Bordure des joueurs de la première bêta.",
        "color_from": "#bcdcf0", "color_to": "#4a7fb5",
    },
    {
        "id": "frame_beta_vert_de_gris", "name": "Vert-de-gris",
        "description": "Bordure des joueurs de la première bêta.",
        "color_from": "#8fc4a8", "color_to": "#2f5d4a",
    },
    {
        "id": "frame_beta_prune", "name": "Prune",
        "description": "Bordure des joueurs de la première bêta.",
        "color_from": "#b085c8", "color_to": "#4a2d6b",
    },
    {
        "id": "frame_beta_ambre", "name": "Ambre pâle",
        "description": "Bordure des joueurs de la première bêta.",
        "color_from": "#f0c27b", "color_to": "#a8692a",
    },
)


async def seed_frames(session: AsyncSession) -> None:
    """Crée les cinq bordures si elles manquent. Ne réécrit jamais une bordure
    existante : nom et couleurs restent modifiables depuis l'admin."""
    existing = set((await session.execute(select(Cosmetic.id))).scalars().all())
    for frame in _FRAMES:
        if frame["id"] not in existing:
            session.add(Cosmetic(kind="avatar_frame", animation="none", **frame))
