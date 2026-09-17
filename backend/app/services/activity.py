"""
Compteurs d'activité alimentant statistiques, achievements et quêtes :
cartes rares obtenues (booster / reroll) et rerolls utilisés.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import UserCard
from app.models.user import User
from app.services import quest_progress
from app.services.power import combined_rarity
from app.services.tier_order import rank


def _is_rare_or_better(rarity_id: str) -> bool:
    return rank("rarity", rarity_id) >= rank("rarity", "rare")


async def track_cards_obtained(session: AsyncSession, user_id: int, rarity_ids: list[str]) -> None:
    """Quêtes « obtenir des cartes rares / légendaires ». Ne commit pas."""
    rares = sum(1 for r in rarity_ids if _is_rare_or_better(r))
    legendaries = sum(1 for r in rarity_ids if r == "legendary")
    if rares:
        await quest_progress.increment(session, user_id, "rare_cards_obtained", rares)
    if legendaries:
        await quest_progress.increment(session, user_id, "legendary_cards_obtained", legendaries)


async def track_reroll(session: AsyncSession, user: User, previous_rarity_id: str, card: UserCard) -> None:
    """Un reroll vient d'être appliqué à `card`. Ne commit pas."""
    user.rerolls_used += 1
    await quest_progress.increment(session, user.id, "rerolls_used", 1)

    if rank("rarity", card.rarity_id) > rank("rarity", previous_rarity_id):
        user.reroll_rarity_upgrades += 1
        await track_cards_obtained(session, user.id, [card.rarity_id])

    luck = combined_rarity(
        card.power, card.drop_probability, card.rarity_id, card.quality_id, card.specialty_id, card.jewelry_id,
    )
    if luck and luck > (user.best_reroll_combined_rarity or 0):
        user.best_reroll_combined_rarity = luck
        user.best_reroll_card_id = card.id
    session.add(user)
