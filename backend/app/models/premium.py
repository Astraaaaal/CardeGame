"""
Boutique premium — cosmétiques, produits vendus en euros (via Stripe) et
commandes. La boutique est désactivée tant que GameConfig.premium_shop_enabled
est faux (seuls les comptes testeurs y ont accès, cf. app/services/premium.py).

La monnaie premium ("Éclats", ressource `shards`) est une ressource comme
les autres mais non échangeable (Resource.tradeable = False).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column, ForeignKey, Integer
from sqlmodel import SQLModel, Field

COSMETIC_KINDS = ("avatar_frame", "showcase_background")
COSMETIC_ANIMATIONS = ("none", "shine", "pulse", "rainbow")

ORDER_PENDING = "pending"
ORDER_PAID = "paid"
ORDER_FAILED = "failed"
ORDER_REFUNDED = "refunded"


class Cosmetic(SQLModel, table=True):
    """Élément purement visuel. Style par défaut en dégradé de couleurs
    (+ animation optionnelle) ; `image_url` (fichier dans web/public/cosmetics/)
    remplace ce style quand il est renseigné."""
    __tablename__ = "cosmetics"

    id: str = Field(primary_key=True, max_length=40)
    kind: str = Field(max_length=30)  # avatar_frame | showcase_background
    name: str = Field(max_length=60)
    description: str = Field(default="")
    color_from: str = Field(default="#8b5cf6", max_length=9)
    color_to: str = Field(default="#22d3ee", max_length=9)
    animation: str = Field(default="none", max_length=20)
    image_url: str = Field(default="", max_length=300)
    active: bool = Field(default=True)


class UserCosmetic(SQLModel, table=True):
    __tablename__ = "user_cosmetics"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    cosmetic_id: str = Field(foreign_key="cosmetics.id", primary_key=True, max_length=40)
    obtained_at: datetime = Field(default_factory=datetime.utcnow)


class PremiumProduct(SQLModel, table=True):
    """Produit vendu en euros : un pack d'Éclats ou un lot (Éclats + ressources
    + boosters + cosmétiques). `grants` = liste de {"kind", "id", "amount"}
    avec kind ∈ resource | booster | cosmetic (les Éclats sont une ressource)."""
    __tablename__ = "premium_products"

    id: str = Field(primary_key=True, max_length=40)
    name: str = Field(max_length=80)
    description: str = Field(default="")
    price_cents: int = Field(default=0)
    currency: str = Field(default="eur", max_length=3)
    grants: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False, default=list))
    # Limite d'achat : période (cf. app/services/purchase_limits.py) et nombre
    # autorisé sur cette période. `once_per_account` (historique) est reprise
    # en "account" par la migration.
    limit_period: str = Field(default="none", max_length=10)
    limit_count: int = Field(default=1)
    once_per_account: bool = Field(default=False)
    active: bool = Field(default=True)
    sort_order: int = Field(default=0)


class PremiumOrder(SQLModel, table=True):
    """Commande en euros. Créée en `pending` à l'ouverture du paiement Stripe,
    passée en `paid` (et créditée) uniquement par le webhook Stripe. Conservée
    même si le compte est supprimé (user_id remis à NULL) : trace comptable."""
    __tablename__ = "premium_orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True),
    )
    product_id: str = Field(max_length=40)
    product_name: str = Field(max_length=80)
    amount_cents: int = Field(default=0)
    currency: str = Field(default="eur", max_length=3)
    grants: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False, default=list))
    status: str = Field(default=ORDER_PENDING, max_length=20)
    stripe_session_id: Optional[str] = Field(default=None, max_length=255, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    paid_at: Optional[datetime] = Field(default=None)
