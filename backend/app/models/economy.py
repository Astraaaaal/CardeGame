"""
Modèles économie secondaire — ressources (recyclage), shop.
"""

from datetime import date, datetime
from typing import Optional
from sqlalchemy import JSON, Column
from sqlmodel import SQLModel, Field


class Resource(SQLModel, table=True):
    """Une ressource (monnaie secondaire) obtenue par recyclage, dépensée au shop."""
    __tablename__ = "resources"

    id: str = Field(primary_key=True, max_length=30)  # slug, ex: "dust"
    name: str = Field(max_length=50)                   # ex: "Poussière"
    description: str = Field(default="")
    # Ressource système (ex: "coins") : non supprimable/non éditable depuis
    # l'admin, existe par défaut pour chaque joueur via User.coins.
    protected: bool = Field(default=False)
    # Solde accordé à la création d'un compte (cf. app/services/auth_service.py).
    # Pour "coins", crédité directement sur User.coins ; pour les autres,
    # une ligne UserResource n'est créée que si > 0.
    starting_amount: int = Field(default=0)
    # Faux pour la monnaie premium : ni échange, ni cadeau, ni prix en vitrine.
    tradeable: bool = Field(default=True)


class UserResource(SQLModel, table=True):
    """Solde d'un joueur pour une ressource donnée."""
    __tablename__ = "user_resources"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    resource_id: str = Field(foreign_key="resources.id", primary_key=True, max_length=30)
    amount: int = Field(default=0)


class ShopOffer(SQLModel, table=True):
    """
    Offre du shop à ressources. Une table unique, plusieurs `kind` :
    - "booster"          : ouvre 1 pack du booster `booster_id`
    - "specific_card"    : donne directement une carte avec la combinaison fixée
    - "reroll"           : re-tire au hasard un ou plusieurs axes d'une carte
                            déjà possédée (rareté/qualité/spécialité/jewelry)
    - "cosmetic"         : débloque un cosmétique (cf. app/models/premium.py)
    - "bundle"           : un lot de plusieurs contenus (`grants`), même format
                            que les produits premium : ressources (Éclats
                            compris), boosters, cosmétiques
    Les colonnes non pertinentes pour un `kind` donné restent NULL.
    """
    __tablename__ = "shop_offers"

    id: str = Field(primary_key=True, max_length=30)
    kind: str = Field(max_length=20)
    name: str = Field(max_length=100)
    description: str = Field(default="")
    active: bool = Field(default=True)

    resource_id: str = Field(foreign_key="resources.id", max_length=30)
    price: int = Field(default=0)

    # Limite d'achat (par joueur, par jour) — générique, utile pour un booster
    # du jour comme pour n'importe quelle offre qu'on veut rationner.
    purchase_limit_per_day: Optional[int] = Field(default=None)
    # Fait partie de la rotation quotidienne automatique (cf. daily_features).
    is_daily_pool: bool = Field(default=False)

    # kind = booster
    booster_id: Optional[str] = Field(default=None, foreign_key="boosters.id", max_length=30)
    # Override optionnel des probabilités DE CETTE OFFRE UNIQUEMENT (n'affecte
    # pas l'ouverture normale du même booster en pièces) :
    force_min_rarity_id: Optional[str] = Field(default=None, foreign_key="rarities.id", max_length=20)
    rarity_weight_multiplier: Optional[float] = Field(default=None)

    # kind = specific_card
    character_id: Optional[str] = Field(default=None, foreign_key="characters.id", max_length=30)
    rarity_id: Optional[str] = Field(default=None, foreign_key="rarities.id", max_length=20)
    quality_id: Optional[str] = Field(default=None, foreign_key="qualities.id", max_length=20)
    specialty_id: Optional[str] = Field(default=None, foreign_key="specialties.id", max_length=20)
    jewelry_id: Optional[str] = Field(default=None, foreign_key="jewelries.id", max_length=20)
    # Puissance de la carte vendue : "rolled" = tirée à l'achat selon la vraie
    # probabilité de la combinaison, "fixed" = card_power (plafonnée au maximum possible).
    # kind = bundle : contenu du lot, liste de {"kind", "id", "amount"}.
    grants: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False, default=list))

    # Limite d'achat : période (cf. app/services/purchase_limits.py) et nombre
    # autorisé sur cette période. `purchase_limit_per_day` reste renseignée
    # pour les offres créées avant cette option.
    limit_period: str = Field(default="none", max_length=10)
    limit_count: int = Field(default=1)

    card_power_mode: str = Field(default="rolled", max_length=10)
    card_power: Optional[int] = Field(default=None)

    # kind = reroll (axes concernés + mode)
    reroll_rarity: bool = Field(default=False)
    reroll_quality: bool = Field(default=False)
    reroll_specialty: bool = Field(default=False)
    reroll_jewelry: bool = Field(default=False)
    # Puissance : peut être retirée seule (même combinaison, nouveau tirage
    # dans sa plage) ou en plus d'un autre axe (qui rerolle de toute façon la
    # puissance puisque la plage change avec la combinaison).
    reroll_power: bool = Field(default=False)
    reroll_mode: Optional[str] = Field(default=None, max_length=20)  # random | guaranteed_min

    # kind = "cosmetic" : cosmétique débloqué à l'achat (cf. app/models/premium.py).
    cosmetic_id: Optional[str] = Field(default=None, max_length=40)


class ShopPurchase(SQLModel, table=True):
    """Journal des achats — sert à appliquer purchase_limit_per_day."""
    __tablename__ = "shop_purchases"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    offer_id: str = Field(foreign_key="shop_offers.id", max_length=30, index=True)
    purchased_at: datetime = Field(default_factory=datetime.utcnow)


class DailyFeature(SQLModel, table=True):
    """
    Épingle manuelle d'une offre pour une date donnée (booster du jour choisi
    à la main). Sans ligne pour aujourd'hui, la rotation automatique choisit
    parmi les offres `is_daily_pool=True` (cf. services/daily_feature.py).
    """
    __tablename__ = "daily_features"

    feature_date: date = Field(primary_key=True)
    offer_id: str = Field(foreign_key="shop_offers.id", max_length=30)
