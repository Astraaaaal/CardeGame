"""
Récompenses multiples des messages admin (Message.reward_items) : validation
à l'envoi, aperçu dans la boîte de réception et crédit à la récupération.

Formes d'un élément :
- {"kind": "resource", "id", "amount"}
- {"kind": "booster", "id", "quantity", "force_min_rarity_id"?, "rarity_weight_multiplier"?, "label"?}
- {"kind": "reroll", "label", "quantity", "rules": {reroll_rarity, ..., reroll_mode}}
- {"kind": "card", "character_id", "rarity_id", "quality_id", "specialty_id", "jewelry_id",
   "power_mode": "rolled" | "fixed", "power"?}  (+ "card_id" une fois récupérée)
"""

from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.booster import Booster
from app.models.card import UserCard
from app.models.character import Character, CharacterSet
from app.models.economy import Resource
from app.models.reference import Rarity, Quality, Specialty, Jewelry
from app.models.user import User
from app.services import booster_inventory, reroll_inventory
from app.services.card_view import build_card_response
from app.services.reroll import assign_bought_card_power
from app.services.wallet import COINS_ID, apply_delta

_RULE_KEYS = ("reroll_rarity", "reroll_quality", "reroll_specialty", "reroll_jewelry", "reroll_power")
_CARD_REFS = (
    ("character_id", Character, "Personnage"), ("rarity_id", Rarity, "Rareté"), ("quality_id", Quality, "Qualité"),
    ("specialty_id", Specialty, "Spécialité"), ("jewelry_id", Jewelry, "Bijou"),
)


def _positive(value, label: str) -> int:
    if not isinstance(value, int) or value < 1:
        raise HTTPException(400, f"{label} : quantité invalide.")
    return value


async def validate(session: AsyncSession, items: list[dict]) -> list[dict]:
    """Normalise et vérifie les récompenses d'un message admin."""
    clean = []
    for item in items:
        kind = item.get("kind")
        if kind == "resource":
            rid = item.get("id")
            if rid != COINS_ID and not await session.get(Resource, rid):
                raise HTTPException(404, f"Ressource « {rid} » introuvable.")
            clean.append({"kind": kind, "id": rid, "amount": _positive(item.get("amount"), "Ressource")})
        elif kind == "booster":
            booster = await session.get(Booster, item.get("id"))
            if not booster:
                raise HTTPException(404, "Booster introuvable.")
            min_rarity = item.get("force_min_rarity_id") or None
            if min_rarity and not await session.get(Rarity, min_rarity):
                raise HTTPException(404, "Rareté minimum introuvable.")
            multiplier = item.get("rarity_weight_multiplier") or None
            if multiplier is not None and not (0 < float(multiplier) <= 100):
                raise HTTPException(400, "Multiplicateur de rareté invalide (0 à 100).")
            clean.append({
                "kind": kind, "id": booster.id, "quantity": _positive(item.get("quantity"), "Booster"),
                "force_min_rarity_id": min_rarity,
                "rarity_weight_multiplier": float(multiplier) if multiplier is not None else None,
                "label": (item.get("label") or "").strip()[:100],
            })
        elif kind == "reroll":
            rules_in = item.get("rules") or {}
            rules = {k: bool(rules_in.get(k)) for k in _RULE_KEYS}
            if not any(rules.values()):
                raise HTTPException(400, "Reroll : coche au moins un axe à relancer.")
            mode = rules_in.get("reroll_mode")
            if mode not in ("random", "guaranteed_min"):
                raise HTTPException(400, "Reroll : choisis un mode (aléatoire ou garanti égal ou mieux).")
            rules["reroll_mode"] = mode
            label = (item.get("label") or "").strip()[:100]
            if not label:
                raise HTTPException(400, "Reroll : donne-lui un nom.")
            clean.append({"kind": kind, "label": label, "rules": rules,
                          "quantity": _positive(item.get("quantity"), "Reroll")})
        elif kind == "card":
            card = {"kind": kind}
            for key, model, label in _CARD_REFS:
                if not item.get(key) or not await session.get(model, item[key]):
                    raise HTTPException(400, f"Carte : {label.lower()} manquant(e) ou introuvable.")
                card[key] = item[key]
            mode = item.get("power_mode") or "rolled"
            if mode not in ("rolled", "fixed"):
                raise HTTPException(400, "Carte : mode de puissance invalide.")
            card["power_mode"] = mode
            if mode == "fixed":
                card["power"] = _positive(item.get("power"), "Carte (puissance)")
            clean.append(card)
        else:
            raise HTTPException(400, "Type de récompense invalide.")
    return clean


def _card_from(item: dict, user_id: int = 0) -> UserCard:
    return UserCard(
        user_id=user_id, character_id=item["character_id"], set_id="",
        rarity_id=item["rarity_id"], quality_id=item["quality_id"],
        specialty_id=item["specialty_id"], jewelry_id=item["jewelry_id"],
    )


async def describe(session: AsyncSession, items: list[dict]) -> list[dict]:
    """Aperçu affichable de chaque récompense (nom, quantité, carte)."""
    out = []
    for item in items or []:
        kind = item["kind"]
        entry = {"kind": kind, "name": "", "quantity": 1, "resource_id": None, "booster_id": None,
                 "label": None, "card": None}
        if kind == "resource":
            resource = await session.get(Resource, item["id"])
            entry.update(name="Pièces" if item["id"] == COINS_ID else (resource.name if resource else item["id"]),
                         quantity=item["amount"], resource_id=item["id"])
        elif kind == "booster":
            booster = await session.get(Booster, item["id"])
            entry.update(name=booster.name if booster else item["id"], quantity=item["quantity"],
                         booster_id=item["id"], label=item.get("label") or None)
        elif kind == "reroll":
            entry.update(name=item["label"], quantity=item["quantity"])
        elif kind == "card":
            real = await session.get(UserCard, item["card_id"]) if item.get("card_id") else None
            card = await build_card_response(session, real or _card_from(item))
            if not real and item.get("power_mode") == "fixed":
                card.power = item.get("power")
            entry.update(name=card.character_name, card=card)
        out.append(entry)
    return out


async def grant(session: AsyncSession, recipient: User, items: list[dict]) -> list[dict]:
    """Crédite les récompenses ; renvoie la liste mise à jour (cartes créées). Ne commit pas."""
    updated = []
    for item in items or []:
        item = dict(item)
        kind = item["kind"]
        if kind == "resource":
            await apply_delta(session, recipient, item["id"], item["amount"])
        elif kind == "booster":
            await booster_inventory.grant_bonus(
                session, recipient.id, item["id"], item.get("force_min_rarity_id"),
                item.get("rarity_weight_multiplier"), item.get("label") or "", item["quantity"],
            )
        elif kind == "reroll":
            await reroll_inventory.grant_rules(
                session, recipient.id, None, item["label"], item["rules"], item["quantity"],
            )
        elif kind == "card":
            card = _card_from(item, recipient.id)
            link = (await session.execute(
                select(CharacterSet).where(CharacterSet.character_id == card.character_id)
            )).scalars().first()
            card.set_id = link.set_id if link else ""
            await assign_bought_card_power(session, card, SimpleNamespace(
                card_power_mode=item.get("power_mode", "rolled"), card_power=item.get("power"),
            ))
            session.add(card)
            await session.flush()
            recipient.total_cards += 1
            session.add(recipient)
            item["card_id"] = card.id
        updated.append(item)
    return updated

