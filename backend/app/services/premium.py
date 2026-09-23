"""
Boutique premium : accès (fermée sauf testeurs), cosmétiques possédés/équipés,
commandes en euros et leur crédit une fois le paiement confirmé par Stripe.
"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.models.booster import Booster
from app.models.economy import Resource
from app.models.game_config import GameConfig
from app.models.premium import (
    Cosmetic, UserCosmetic, PremiumProduct, PremiumOrder,
    ORDER_PENDING, ORDER_PAID, ORDER_FAILED, ORDER_REFUNDED,
)
from app.models.user import User
from app.models.distinction import FOUNDER_ID
from app.services import distinctions
from app.services import booster_inventory
from app.services import purchase_limits
from app.services.wallet import apply_delta

PREMIUM_RESOURCE_ID = "shards"


def parse_testers(raw: str) -> set[str]:
    return {name.strip().lower() for name in raw.replace("\n", ",").split(",") if name.strip()}


async def has_access(session: AsyncSession, user: User) -> bool:
    config = await session.get(GameConfig, 1)
    if not config:
        return False
    return config.premium_shop_enabled or user.username.lower() in parse_testers(config.premium_testers)


async def require_access(session: AsyncSession, user: User) -> None:
    if not await has_access(session, user):
        raise HTTPException(403, "La boutique premium n'est pas encore ouverte.")


async def ensure_tradeable(session: AsyncSession, resource_id: str) -> None:
    """Refuse qu'une ressource liée au compte (monnaie premium) circule entre joueurs."""
    resource = await session.get(Resource, resource_id)
    if resource and not resource.tradeable:
        raise HTTPException(400, f"Les {resource.name.lower()} sont liés à ton compte et ne peuvent pas être échangés.")


async def grant_cosmetic(session: AsyncSession, user_id: int, cosmetic_id: str) -> bool:
    """Débloque un cosmétique. Retourne False s'il était déjà possédé. Ne commit pas."""
    if await session.get(UserCosmetic, (user_id, cosmetic_id)):
        return False
    session.add(UserCosmetic(user_id=user_id, cosmetic_id=cosmetic_id))
    return True


async def validate_grants(session: AsyncSession, grants: list[dict]) -> None:
    for grant in grants:
        kind, item_id, amount = grant.get("kind"), grant.get("id"), grant.get("amount", 1)
        if kind not in ("resource", "booster", "cosmetic") or not item_id:
            raise HTTPException(400, "Contenu de lot invalide.")
        if not isinstance(amount, int) or amount < 1:
            raise HTTPException(400, "Chaque élément du lot doit avoir une quantité ≥ 1.")
        model = {"resource": Resource, "booster": Booster, "cosmetic": Cosmetic}[kind]
        if kind != "resource" or item_id != "coins":
            if not await session.get(model, item_id):
                raise HTTPException(400, f"Élément introuvable : {kind} « {item_id} ».")


async def apply_grants(session: AsyncSession, user: User, grants: list[dict]) -> None:
    """Crédite le contenu d'un lot. Ne commit pas."""
    for grant in grants:
        kind, item_id, amount = grant["kind"], grant["id"], int(grant.get("amount", 1))
        if kind == "resource":
            await apply_delta(session, user, item_id, amount)
        elif kind == "booster":
            await booster_inventory.grant(session, user.id, item_id, amount)
        elif kind == "cosmetic":
            await grant_cosmetic(session, user.id, item_id)


def product_limit(product: PremiumProduct) -> tuple[str, int]:
    """Période et nombre autorisé ; reprend l'ancien « une fois par compte »."""
    if product.limit_period != purchase_limits.PERIOD_NONE:
        return product.limit_period, max(1, product.limit_count)
    if product.once_per_account:
        return purchase_limits.PERIOD_ACCOUNT, 1
    return purchase_limits.PERIOD_NONE, 0


async def create_order(session: AsyncSession, user: User, product_id: str) -> PremiumOrder:
    await require_access(session, user)
    product = await session.get(PremiumProduct, product_id)
    if not product or not product.active:
        raise HTTPException(404, "Produit introuvable.")
    period, allowed = product_limit(product)
    if period != purchase_limits.PERIOD_NONE:
        query = select(func.count()).select_from(PremiumOrder).where(
            PremiumOrder.user_id == user.id, PremiumOrder.product_id == product.id,
            PremiumOrder.status == ORDER_PAID,
        )
        start = purchase_limits.window_start(period)
        if start is not None:
            query = query.where(PremiumOrder.paid_at >= start)
        done = (await session.execute(query)).scalar_one()
        if done >= allowed:
            when = purchase_limits.label(period)
            raise HTTPException(409, f"Limite atteinte pour cette offre ({done}/{allowed} {when}).")
    order = PremiumOrder(
        user_id=user.id, product_id=product.id, product_name=product.name,
        amount_cents=product.price_cents, currency=product.currency, grants=list(product.grants),
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


async def fulfill_order(
    session: AsyncSession, order_id: int, stripe_session_id: str | None = None,
    amount_cents: int | None = None, currency: str | None = None,
) -> bool:
    """Crédite une commande payée. Idempotent : un webhook rejoué ne crédite pas deux fois.
    Le contenu crédité est celui figé à la commande (modifier le produit ensuite n'y change rien).
    Refuse un paiement dont le montant ou la devise ne correspond pas à la commande."""
    order = (await session.execute(
        select(PremiumOrder).where(PremiumOrder.id == order_id).with_for_update().execution_options(populate_existing=True)
    )).scalar_one_or_none()
    if not order or order.status != ORDER_PENDING:
        return False
    if stripe_session_id and order.stripe_session_id and order.stripe_session_id != stripe_session_id:
        return False
    if amount_cents != order.amount_cents or (currency or "").lower() != order.currency.lower():
        return False
    user = await session.get(User, order.user_id) if order.user_id else None
    order.status = ORDER_PAID
    order.paid_at = datetime.utcnow()
    session.add(order)
    if user:
        await apply_grants(session, user, order.grants)
        # Soutenir le jeu pendant la bêta vaut la distinction de fondateur ;
        # elle survivra à la remise à zéro, contrairement au contenu crédité.
        await distinctions.grant(
            session, user.id, FOUNDER_ID, reason=f"achat {order.product_id}"
        )
    await session.commit()
    return True


async def _move_order(session: AsyncSession, order_id: int, from_status: str, to_status: str) -> bool:
    order = (await session.execute(
        select(PremiumOrder).where(PremiumOrder.id == order_id).with_for_update().execution_options(populate_existing=True)
    )).scalar_one_or_none()
    if not order or order.status != from_status:
        return False
    order.status = to_status
    session.add(order)
    await session.commit()
    return True


async def expire_order(session: AsyncSession, order_id: int) -> bool:
    """Paiement abandonné ou échoué : la commande en attente passe en « échouée »."""
    return await _move_order(session, order_id, ORDER_PENDING, ORDER_FAILED)


async def refund_order(session: AsyncSession, order_id: int) -> bool:
    """Remboursement fait depuis Stripe : le contenu déjà crédité n'est pas retiré."""
    return await _move_order(session, order_id, ORDER_PAID, ORDER_REFUNDED)


async def owned_cosmetics(session: AsyncSession, user_id: int) -> list[Cosmetic]:
    return list((await session.execute(
        select(Cosmetic).join(UserCosmetic, UserCosmetic.cosmetic_id == Cosmetic.id)
        .where(UserCosmetic.user_id == user_id).order_by(Cosmetic.kind, Cosmetic.name)
    )).scalars().all())


async def equip(session: AsyncSession, user: User, avatar_frame_id: str | None, showcase_background_id: str | None) -> None:
    for kind, cosmetic_id, field in (
        ("avatar_frame", avatar_frame_id, "equipped_avatar_frame_id"),
        ("showcase_background", showcase_background_id, "equipped_showcase_background_id"),
    ):
        if cosmetic_id:
            cosmetic = await session.get(Cosmetic, cosmetic_id)
            if not cosmetic or cosmetic.kind != kind or not await session.get(UserCosmetic, (user.id, cosmetic_id)):
                raise HTTPException(400, "Tu ne possèdes pas ce cosmétique.")
        setattr(user, field, cosmetic_id)
    session.add(user)
    await session.commit()
