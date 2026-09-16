"""
Routes joueur — Profil, daily reward.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete

from app.database import get_session
from app.core.dependencies import get_current_user
from app.core.ratelimit import rate_limit
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.models.token import RefreshToken
from app.models.card import UserCard
from app.models.economy import Resource, UserResource
from app.models.social import TradeListing
from app.models.achievement import UserAchievement
from app.schemas.player import PlayerResponse, DailyRewardResponse, UpdateProfileRequest, PlayerStatsResponse
from app.schemas.auth import ChangePasswordRequest, DeleteAccountRequest, MessageResponse
from app.schemas.economy import ResourceBalance
from app.schemas.showcase import ShowcaseResponse, UpdateShowcaseRequest, UpdateTradeListingsRequest
from app.schemas.settings import PlayerSettings, UpdatePlayerSettings
from app.services.daily_reward import DailyRewardService
from app.services.showcase_view import build_showcase_response, ACHIEVEMENT_SLOT_FIELDS
from app.services.account import delete_account
from app.services.player_stats import build_player_stats

router = APIRouter()
daily_service = DailyRewardService()


async def _profile_response(session: AsyncSession, user: User) -> PlayerResponse:
    resources = (await session.execute(
        select(UserResource, Resource.name)
        .join(Resource, Resource.id == UserResource.resource_id)
        .where(UserResource.user_id == user.id)
    )).all()

    return PlayerResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        coins=user.coins,
        packs_opened=user.packs_opened,
        total_cards=user.total_cards,
        login_streak=user.login_streak,
        created_at=user.created_at,
        last_login=user.last_login,
        resources=[
            ResourceBalance(id=ur.resource_id, name=name, amount=ur.amount)
            for ur, name in resources
        ],
        allow_friend_requests=user.allow_friend_requests,
        trade_request_policy=user.trade_request_policy,
        trade_request_popup_enabled=user.trade_request_popup_enabled,
    )


@router.get("/me", response_model=PlayerResponse)
async def get_profile(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Retourne le profil du joueur connecté, y compris ses ressources."""
    return await _profile_response(session, user)


@router.get("/stats", response_model=PlayerStatsResponse)
async def get_player_stats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Statistiques enrichies pour l'onglet Statistiques du profil (sérieuses + fun)."""
    return await build_player_stats(session, user)


@router.patch("/me", response_model=PlayerResponse)
async def update_profile(
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Modifie le profil du joueur (pour l'instant : le nom affiché)."""
    user.display_name = body.display_name.strip()
    session.add(user)
    await session.commit()
    return await _profile_response(session, user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit(5, 60))],
)
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Change le mot de passe. Révoque tous les refresh tokens existants (y
    compris ceux d'autres appareils) — par sécurité, chaque session doit se
    reconnecter avec le nouveau mot de passe.
    """
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Mot de passe actuel incorrect.")

    user.password_hash = hash_password(body.new_password)
    session.add(user)
    await session.execute(delete(RefreshToken).where(RefreshToken.user_id == user.id))
    await session.commit()
    return MessageResponse(message="Mot de passe changé. Reconnecte-toi.")


@router.delete(
    "/me",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit(5, 60))],
)
async def delete_my_account(
    body: DeleteAccountRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Supprime définitivement le compte (et toutes les données associées),
    après vérification du mot de passe. Irréversible.
    """
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(400, "Mot de passe incorrect.")
    await delete_account(session, user)
    return MessageResponse(message="Compte supprimé.")


@router.put("/showcase", response_model=ShowcaseResponse)
async def update_showcase(
    body: UpdateShowcaseRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Configure la vitrine publique : avatar (un personnage possédé) et jusqu'à
    3 cartes possédées mises en avant. Remplace entièrement la configuration
    précédente (pas de mise à jour partielle).
    """
    if body.avatar_character_id:
        owns_character = (await session.execute(
            select(UserCard).where(
                UserCard.user_id == user.id,
                UserCard.character_id == body.avatar_character_id,
            )
        )).first()
        if not owns_character:
            raise HTTPException(400, "Tu ne possèdes pas ce personnage.")
    user.avatar_character_id = body.avatar_character_id

    slot_fields = ["showcase_card_1_id", "showcase_card_2_id", "showcase_card_3_id"]
    for field, card_id in zip(slot_fields, body.card_slots):
        if card_id:
            card = await session.get(UserCard, card_id)
            if not card or card.user_id != user.id:
                raise HTTPException(400, "Une des cartes choisies ne t'appartient pas.")
        setattr(user, field, card_id)

    chosen = [a for a in body.achievement_slots if a]
    if len(set(chosen)) != len(chosen):
        raise HTTPException(400, "Un même achievement est affiché plusieurs fois.")
    for field, achievement_id in zip(ACHIEVEMENT_SLOT_FIELDS, body.achievement_slots):
        if achievement_id and not await session.get(UserAchievement, (user.id, achievement_id)):
            raise HTTPException(400, "Tu n'as pas encore débloqué cet achievement.")
        setattr(user, field, achievement_id)

    session.add(user)
    await session.commit()
    return await build_showcase_response(session, user)


@router.put("/trade-listings", response_model=ShowcaseResponse)
async def update_trade_listings(
    body: UpdateTradeListingsRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Configure jusqu'à 3 cartes possédées "à échanger", chacune avec un prix
    dans une ressource au choix et un mode : "buy_now" (achat direct
    immédiat par un autre joueur) ou "offer" (prix indicatif, un clic crée
    une demande d'échange). Remplace entièrement la configuration précédente.
    """
    for slot, slot_in in enumerate(body.slots):
        existing = await session.get(TradeListing, (user.id, slot))
        if slot_in is None:
            if existing:
                await session.delete(existing)
            continue

        card = await session.get(UserCard, slot_in.user_card_id)
        if not card or card.user_id != user.id:
            raise HTTPException(400, "Une des cartes choisies ne t'appartient pas.")
        if not await session.get(Resource, slot_in.resource_id):
            raise HTTPException(400, f"La ressource '{slot_in.resource_id}' n'existe pas.")

        if existing:
            existing.user_card_id = slot_in.user_card_id
            existing.resource_id = slot_in.resource_id
            existing.price = slot_in.price
            existing.mode = slot_in.mode
            session.add(existing)
        else:
            session.add(TradeListing(
                user_id=user.id, slot=slot, user_card_id=slot_in.user_card_id,
                resource_id=slot_in.resource_id, price=slot_in.price, mode=slot_in.mode,
            ))

    await session.commit()
    return await build_showcase_response(session, user)


@router.get("/settings", response_model=PlayerSettings)
async def get_settings(user: User = Depends(get_current_user)):
    return PlayerSettings(
        allow_friend_requests=user.allow_friend_requests,
        trade_request_policy=user.trade_request_policy,
        trade_request_popup_enabled=user.trade_request_popup_enabled,
        gift_policy=user.gift_policy,
    )


@router.patch("/settings", response_model=PlayerSettings)
async def update_settings(
    body: UpdatePlayerSettings,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Paramètres sociaux : qui peut envoyer une demande d'ami / d'échange, popup de notif."""
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(user, k, v)
    session.add(user)
    await session.commit()
    return PlayerSettings(
        allow_friend_requests=user.allow_friend_requests,
        trade_request_policy=user.trade_request_policy,
        trade_request_popup_enabled=user.trade_request_popup_enabled,
        gift_policy=user.gift_policy,
    )


@router.post("/daily-reward", response_model=DailyRewardResponse)
async def claim_daily_reward(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Réclame la récompense journalière (streak)."""
    result = await daily_service.check_and_claim(session, user)
    return DailyRewardResponse(**result)
