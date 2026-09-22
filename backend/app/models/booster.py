"""
Modèle Booster — Packs achetables.
"""

from sqlmodel import SQLModel, Field


class Booster(SQLModel, table=True):
    __tablename__ = "boosters"

    id: str = Field(primary_key=True, max_length=30)
    name: str = Field(max_length=100)
    # Set "principal" (compat historique). La liste complète des sets d'un
    # booster vit dans BoosterSet ; set_id = le premier de cette liste.
    set_id: str = Field(foreign_key="sets.id", max_length=20)
    cards_count: int = Field(default=5)
    # Monnaie utilisée pour l'achat classique de ce booster. "coins" est un
    # id de ressource réservé, routé vers User.coins (cf. services/wallet.py).
    resource_id: str = Field(default="coins", foreign_key="resources.id", max_length=30)
    price: int = Field(default=100)
    guaranteed_rare: bool = Field(default=False)
    description: str = Field(default="")
    # Nom de fichier dans web/public/boosters/ (même convention que
    # Character.image_url) ; remplace le visuel générique du dos de pack
    # (voir CardReveal côté web) et l'illustration dans la boutique.
    cover_image_url: str = Field(default="", max_length=300)

    # Interrupteur global : si False, ce booster n'est ouvrable nulle part
    # (ni boutique classique, ni offre du shop à ressources).
    active: bool = Field(default=True)
    # Si False, masqué de la boutique classique (pièces) mais reste ouvrable
    # via une offre du shop à ressources qui le référence explicitement —
    # utile pour vendre un vieux booster "hors rotation" plus cher ailleurs.
    visible_in_shop: bool = Field(default=True)


class BoosterSet(SQLModel, table=True):
    """Table de liaison booster <-> sets : un booster peut piocher dans plusieurs sets."""
    __tablename__ = "booster_sets"

    booster_id: str = Field(foreign_key="boosters.id", primary_key=True, max_length=30)
    set_id: str = Field(foreign_key="sets.id", primary_key=True, max_length=20)
