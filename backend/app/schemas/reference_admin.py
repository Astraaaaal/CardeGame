"""
Schema — édition admin des barèmes de tirage (rareté / qualité / spécialité
/ bijou) : poids (probabilité de tirage) et valeur de recyclage.
Les 4 tables partagent exactement les mêmes champs réglables.
"""

from pydantic import BaseModel


class TuningPatch(BaseModel):
    weight: float | None = None
