"""
Rerolls achetés dans le shop à ressources et gardés pour plus tard.
"""

from typing import Optional

from sqlmodel import SQLModel, Field


class UserRerollToken(SQLModel, table=True):
    """Reroll non utilisé : garde les règles de l'offre au moment de l'achat
    (axes relancés, puissance, mode), même si l'offre change ou disparaît
    ensuite. Les exemplaires aux règles identiques sont cumulés sur une ligne."""
    __tablename__ = "user_reroll_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    # Offre d'origine, sans clé étrangère : sert seulement à afficher le stock
    # sur l'offre dans la boutique ; l'offre peut avoir été supprimée depuis.
    offer_id: Optional[str] = Field(default=None, max_length=30)
    label: str = Field(default="", max_length=100)
    reroll_rarity: bool = Field(default=False)
    reroll_quality: bool = Field(default=False)
    reroll_specialty: bool = Field(default=False)
    reroll_jewelry: bool = Field(default=False)
    reroll_power: bool = Field(default=False)
    reroll_mode: Optional[str] = Field(default=None, max_length=20)
    # Machine d'amélioration : multiplie les chances des paliers meilleurs que
    # l'actuel sur les axes relancés (None = chances normales).
    reroll_boost: Optional[float] = Field(default=None)
    quantity: int = Field(default=0)
