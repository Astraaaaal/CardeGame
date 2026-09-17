"""
Routes — boutique premium (joueur) + webhook Stripe + administration.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.core.dependencies import get_current_user, require_admin
from app.core.ratelimit import rate_limit
from app.database import get_session
from app.models.booster import Booster
from app.models.economy import Resource, ShopOffer
from app.models.game_config import GameConfig
from app.models.premium import Cosmetic, UserCosmetic, PremiumProduct, PremiumOrder, ORDER_PAID
from app.models.user import User
from app.schemas.premium import (
    CosmeticOut, CosmeticIn, CosmeticPatch, GrantOut,
    PremiumProductOut, PremiumProductIn, PremiumProductPatch,
    PremiumStatusOut, CheckoutRequest, CheckoutResponse,
    MyCosmeticsOut, EquipCosmeticsRequest,
    PremiumOrderOut, PremiumConfigOut, PremiumConfigPatch,
)
from app.services import premium as svc
from app.services import stripe_client
from app.services.wallet import get_balance

logger = logging.getLogger(__name__)

router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(require_admin)])


def _cosmetic_out(c: Cosmetic) -> CosmeticOut:
    return CosmeticOut(
        id=c.id, kind=c.kind, name=c.name, description=c.description, color_from=c.color_from,
        color_to=c.color_to, animation=c.animation, image_url=c.image_url, active=c.active,
    )


async def _grant_name(session: AsyncSession, kind: str, item_id: str) -> str:
    if kind == "resource" and item_id == "coins":
        return "Pièces"
    model = {"resource": Resource, "booster": Booster, "cosmetic": Cosmetic}[kind]
    row = await session.get(model, item_id)
    return row.name if row else item_id


async def _product_out(session: AsyncSession, p: PremiumProduct, user_id: int | None = None) -> PremiumProductOut:
    already = False
    if user_id is not None and p.once_per_account:
        already = bool((await session.execute(select(PremiumOrder.id).where(
            PremiumOrder.user_id == user_id, PremiumOrder.product_id == p.id, PremiumOrder.status == ORDER_PAID,
        ))).first())
    return PremiumProductOut(
        id=p.id, name=p.name, description=p.description, price_cents=p.price_cents, currency=p.currency,
        grants=[GrantOut(**g, name=await _grant_name(session, g["kind"], g["id"])) for g in p.grants],
        once_per_account=p.once_per_account, already_purchased=already, active=p.active, sort_order=p.sort_order,
    )


# ─────────────────────────────  JOUEUR  ─────────────────────────────

@router.get("/status", response_model=PremiumStatusOut)
async def premium_status(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return PremiumStatusOut(
        access=await svc.has_access(session, user),
        shards=await get_balance(session, user, svc.PREMIUM_RESOURCE_ID),
        payments_available=stripe_client.is_configured(),
    )


@router.get("/products", response_model=list[PremiumProductOut])
async def list_products(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await svc.require_access(session, user)
    rows = (await session.execute(
        select(PremiumProduct).where(PremiumProduct.active == True)  # noqa: E712
        .order_by(PremiumProduct.sort_order, PremiumProduct.price_cents)
    )).scalars().all()
    return [await _product_out(session, p, user.id) for p in rows]


@router.post("/checkout", response_model=CheckoutResponse, dependencies=[Depends(rate_limit(10, 60))])
async def checkout(body: CheckoutRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    """Ouvre un paiement Stripe. Le crédit n'a lieu qu'à la confirmation par webhook."""
    await svc.require_access(session, user)
    if not stripe_client.is_configured():
        raise HTTPException(503, "Les paiements ne sont pas encore disponibles.")
    order = await svc.create_order(session, user, body.product_id)
    stripe_session_id, url = await stripe_client.create_checkout_session(
        order_id=order.id, product_name=order.product_name, amount_cents=order.amount_cents,
        currency=order.currency, customer_email=user.email,
    )
    order.stripe_session_id = stripe_session_id
    session.add(order)
    await session.commit()
    return CheckoutResponse(url=url)


@router.post("/stripe-webhook", include_in_schema=False)
async def stripe_webhook(request: Request, session: AsyncSession = Depends(get_session)):
    if not stripe_client.is_configured():
        raise HTTPException(503, "Paiements non configurés.")
    payload = await request.body()
    if not stripe_client.verify_webhook_signature(
        payload, request.headers.get("stripe-signature", ""), settings.STRIPE_WEBHOOK_SECRET,
    ):
        raise HTTPException(400, "Signature invalide.")

    event = json.loads(payload)
    event_type = event.get("type")
    obj = event.get("data", {}).get("object", {})
    raw_order_id = obj.get("metadata", {}).get("order_id") or obj.get("client_reference_id")
    order_id = int(raw_order_id) if raw_order_id and str(raw_order_id).isdigit() else None

    if event_type in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        if obj.get("payment_status") == "paid" and order_id:
            if not await svc.fulfill_order(session, order_id, obj.get("id"), obj.get("amount_total"), obj.get("currency")):
                logger.info("Webhook Stripe sans crédit (commande %s déjà traitée ou incohérente)", order_id)
    elif event_type in ("checkout.session.expired", "checkout.session.async_payment_failed"):
        if order_id:
            await svc.expire_order(session, order_id)
    elif event_type == "charge.refunded":
        # Remboursement fait depuis Stripe : la commande passe en « remboursée »,
        # le contenu déjà crédité n'est pas retiré automatiquement (au cas par cas).
        payment_intent = obj.get("payment_intent")
        found = await stripe_client.find_order_id_for_payment_intent(payment_intent) if payment_intent else None
        if found and str(found).isdigit():
            await svc.refund_order(session, int(found))
        logger.warning("Remboursement Stripe reçu (payment_intent=%s, commande=%s)", payment_intent, found)
    return {"received": True}


@router.get("/cosmetics", response_model=list[CosmeticOut])
async def list_cosmetics(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    """Cosmétiques actifs — pour prévisualiser ceux vendus dans la boutique premium."""
    await svc.require_access(session, user)
    rows = (await session.execute(
        select(Cosmetic).where(Cosmetic.active == True).order_by(Cosmetic.kind, Cosmetic.name)  # noqa: E712
    )).scalars().all()
    return [_cosmetic_out(c) for c in rows]


@router.get("/cosmetics/mine", response_model=MyCosmeticsOut)
async def my_cosmetics(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return MyCosmeticsOut(
        owned=[_cosmetic_out(c) for c in await svc.owned_cosmetics(session, user.id)],
        equipped_avatar_frame_id=user.equipped_avatar_frame_id,
        equipped_showcase_background_id=user.equipped_showcase_background_id,
    )


@router.put("/cosmetics/equip", response_model=MyCosmeticsOut)
async def equip_cosmetics(
    body: EquipCosmeticsRequest, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session),
):
    await svc.equip(session, user, body.avatar_frame_id, body.showcase_background_id)
    return await my_cosmetics(user, session)


# ─────────────────────────────  ADMIN  ─────────────────────────────

@admin_router.get("/config", response_model=PremiumConfigOut)
async def get_config(session: AsyncSession = Depends(get_session)):
    config = await session.get(GameConfig, 1) or GameConfig()
    return PremiumConfigOut(
        premium_shop_enabled=config.premium_shop_enabled, premium_testers=config.premium_testers,
        stripe_configured=stripe_client.is_configured(), email_configured=bool(settings.BREVO_API_KEY),
    )


@admin_router.patch("/config", response_model=PremiumConfigOut)
async def update_config(body: PremiumConfigPatch, session: AsyncSession = Depends(get_session)):
    config = await session.get(GameConfig, 1) or GameConfig(id=1)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(config, key, value)
    session.add(config)
    await session.commit()
    return await get_config(session)


@admin_router.get("/cosmetics", response_model=list[CosmeticOut])
async def admin_list_cosmetics(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Cosmetic).order_by(Cosmetic.kind, Cosmetic.name))).scalars().all()
    return [_cosmetic_out(c) for c in rows]


@admin_router.post("/cosmetics", response_model=CosmeticOut, status_code=201)
async def admin_create_cosmetic(body: CosmeticIn, session: AsyncSession = Depends(get_session)):
    if await session.get(Cosmetic, body.id):
        raise HTTPException(409, f"Le cosmétique '{body.id}' existe déjà.")
    cosmetic = Cosmetic(**body.model_dump())
    session.add(cosmetic)
    await session.commit()
    return _cosmetic_out(cosmetic)


@admin_router.patch("/cosmetics/{cosmetic_id}", response_model=CosmeticOut)
async def admin_update_cosmetic(cosmetic_id: str, body: CosmeticPatch, session: AsyncSession = Depends(get_session)):
    cosmetic = await session.get(Cosmetic, cosmetic_id)
    if not cosmetic:
        raise HTTPException(404, "Cosmétique introuvable.")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(cosmetic, key, value)
    session.add(cosmetic)
    await session.commit()
    return _cosmetic_out(cosmetic)


@admin_router.delete("/cosmetics/{cosmetic_id}", status_code=204)
async def admin_delete_cosmetic(cosmetic_id: str, session: AsyncSession = Depends(get_session)):
    cosmetic = await session.get(Cosmetic, cosmetic_id)
    if not cosmetic:
        raise HTTPException(404, "Cosmétique introuvable.")
    owners = (await session.execute(select(UserCosmetic).where(UserCosmetic.cosmetic_id == cosmetic_id))).first()
    offers = (await session.execute(select(ShopOffer.id).where(ShopOffer.cosmetic_id == cosmetic_id))).first()
    if owners or offers:
        raise HTTPException(409, "Cosmétique déjà possédé par des joueurs ou vendu dans une offre : désactive-le plutôt.")
    await session.delete(cosmetic)
    await session.commit()


@admin_router.get("/products", response_model=list[PremiumProductOut])
async def admin_list_products(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(PremiumProduct).order_by(PremiumProduct.sort_order))).scalars().all()
    return [await _product_out(session, p) for p in rows]


@admin_router.post("/products", response_model=PremiumProductOut, status_code=201)
async def admin_create_product(body: PremiumProductIn, session: AsyncSession = Depends(get_session)):
    if await session.get(PremiumProduct, body.id):
        raise HTTPException(409, f"Le produit '{body.id}' existe déjà.")
    grants = [g.model_dump() for g in body.grants]
    await svc.validate_grants(session, grants)
    product = PremiumProduct(**body.model_dump(exclude={"grants"}), grants=grants)
    session.add(product)
    await session.commit()
    return await _product_out(session, product)


@admin_router.patch("/products/{product_id}", response_model=PremiumProductOut)
async def admin_update_product(product_id: str, body: PremiumProductPatch, session: AsyncSession = Depends(get_session)):
    product = await session.get(PremiumProduct, product_id)
    if not product:
        raise HTTPException(404, "Produit introuvable.")
    data = body.model_dump(exclude_unset=True)
    if "grants" in data:
        await svc.validate_grants(session, data["grants"])
    for key, value in data.items():
        setattr(product, key, value)
    session.add(product)
    await session.commit()
    return await _product_out(session, product)


@admin_router.delete("/products/{product_id}", status_code=204)
async def admin_delete_product(product_id: str, session: AsyncSession = Depends(get_session)):
    product = await session.get(PremiumProduct, product_id)
    if not product:
        raise HTTPException(404, "Produit introuvable.")
    if (await session.execute(select(PremiumOrder.id).where(PremiumOrder.product_id == product_id))).first():
        raise HTTPException(409, "Produit déjà commandé : désactive-le plutôt (historique des commandes).")
    await session.delete(product)
    await session.commit()


@admin_router.get("/orders", response_model=list[PremiumOrderOut])
async def admin_list_orders(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(
        select(PremiumOrder, User.username).join(User, User.id == PremiumOrder.user_id, isouter=True)
        .order_by(PremiumOrder.created_at.desc()).limit(200)
    )).all()
    return [
        PremiumOrderOut(
            id=o.id, username=username, product_name=o.product_name, amount_cents=o.amount_cents,
            currency=o.currency, status=o.status, created_at=o.created_at, paid_at=o.paid_at,
        )
        for o, username in rows
    ]
