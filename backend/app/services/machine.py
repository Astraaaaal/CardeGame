"""
Machine d'amélioration et convertisseur de ressources (onglet Activités).

Machine : on paie des pièces pour améliorer d'un cran un booster ou un reroll
possédé. L'amélioration proposée dépend du jour (rotation réglable) et parfois
d'un événement aléatoire commun à tous (jour risqué, soldes, jour de chance).
Chaque cran est plus cher et moins probable que le précédent ; un échec coûte
le paiement (l'objet reste, sauf jour risqué) et rend le prochain essai un peu
plus probable mais plus cher. Tout revient à zéro après une réussite.

À partir d'un certain cran, une ressource liée à l'amélioration est aussi
demandée (fragments pour la rareté, minerais pour le bijou…). Dès le premier
cran, on peut en ajouter pour augmenter la réussite, dans la limite d'un
plafond qui baisse avec le cran : un palier rare n'est jamais garanti.

Convertisseur : échange de ressources avec perte, quelques fois par jour,
pour compléter une ressource qui manque — pas pour s'enrichir.
"""

import logging
import random
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.booster import Booster
from app.models.booster_inventory import UserBonusBooster, UserBoosterInventory
from app.models.economy import Resource
from app.models.reference import Jewelry, Quality, Rarity
from app.models.reroll_inventory import UserRerollToken
from app.models.user import User
from app.services import activities_config, booster_inventory, reroll_inventory
from app.services.presence_bonus import get_activity
from app.services.reroll import reroll_axes
from app.services.tier_order import rank
from app.services import unlocks
from app.services.wallet import apply_delta, require_balance

MAX_EXTRA_PER_RESOURCE = 1000

# Améliorations de booster : champ du bonus modifié et paliers successifs.
BOOSTER_LADDERS = {
    "rarity_chances": ("rarity_weight_multiplier", [1.5, 2.0, 3.0, 5.0]),
    "rarity_guarantee": ("force_min_rarity_id", ["rare", "epic", "legendary"]),
    "quality_guarantee": ("min_quality_id", ["preserved", "excellent", "graded", "mint", "authentic"]),
    "jewelry_guarantee": ("min_jewelry_id", ["silver", "gold", "diamond", "prismatic"]),
    "specialty_chances": ("specialty_weight_multiplier", [1.5, 2.0, 3.0, 5.0]),
    "quality_chances": ("quality_weight_multiplier", [1.5, 2.0, 3.0, 5.0]),
    "jewelry_chances": ("jewelry_weight_multiplier", [1.5, 2.0, 3.0, 5.0]),
    "power_chances": ("power_rolls", [2, 3, 4, 5]),
}
_AXIS_OF_FIELD = {"force_min_rarity_id": "rarity", "min_quality_id": "quality", "min_jewelry_id": "jewelry"}
REROLL_KINDS = ("reroll_guarantee", "reroll_axis", "reroll_boost")
REROLL_BOOSTS = [1.5, 2.0, 3.0]
AXES = ("rarity", "quality", "specialty", "jewelry")
AXIS_LABEL = {"rarity": "rareté", "quality": "qualité", "specialty": "spécialité", "jewelry": "bijou"}
KIND_LABEL = {
    "rarity_chances": "Chances de rareté boostées",
    "rarity_guarantee": "Rareté garantie",
    "quality_guarantee": "Qualité garantie",
    "jewelry_guarantee": "Bijou garanti",
    "specialty_chances": "Chances de spécialité boostées",
    "quality_chances": "Chances de qualité boostées",
    "jewelry_chances": "Chances de bijou boostées",
    "power_chances": "Chances de puissance boostées",
    "reroll_guarantee": "Reroll garanti",
    "reroll_axis": "Axe de reroll en plus",
    "reroll_boost": "Chances de reroll boostées",
}
logger = logging.getLogger(__name__)


# ─────────────────────────────  JOUR ET ÉVÉNEMENT  ─────────────────────────────

def today_plan(cfg: dict, now: datetime | None = None) -> dict:
    """Jour du cycle : les améliorations et les événements se partagent les jours
    du cycle, dans un ordre tiré au hasard à chaque nouveau cycle (graine = numéro
    du cycle : identique pour tout le monde, imprévisible d'un cycle à l'autre)."""
    now = now or datetime.utcnow()
    machine = cfg["machine"]
    upgrades = [k for k in machine["cycle_upgrades"] if k in KIND_LABEL]
    slots = [("upgrade", k) for k in upgrades] + [("event", e) for e in machine["events"]]
    if not slots:
        return {"day": 1, "length": 1, "kinds": [], "event": None}
    start = date.fromisoformat(machine.get("cycle_start") or "2026-09-21")
    days = (now.date() - start).days
    cycle, day = divmod(days, len(slots))
    order = slots[:]
    random.Random(f"machine-cycle-{cycle}").shuffle(order)
    kind, value = order[day]
    if kind == "upgrade":
        return {"day": day + 1, "length": len(slots), "kinds": [value], "event": None}
    # Jour d'événement : une amélioration tirée au hasard, avec l'effet de l'événement.
    picked = random.Random(f"machine-event-{cycle}-{day}").choice(upgrades) if upgrades else None
    return {"day": day + 1, "length": len(slots), "kinds": [picked] if picked else [], "event": value}


# ─────────────────────────────  NIVEAUX  ─────────────────────────────

def _numeric_level(ladder: list[float], value) -> tuple[int, float | None]:
    level = sum(1 for v in ladder if value and v <= value)
    nxt = next((v for v in ladder if not value or v > value), None)
    return level, nxt


def _id_level(axis: str, ladder: list[str], value) -> tuple[int, str | None]:
    current = rank(axis, value) if value else -1
    level = sum(1 for v in ladder if value and rank(axis, v) <= current)
    nxt = next((v for v in ladder if rank(axis, v) > current), None)
    return level, nxt


def booster_step(kind: str, bonus: dict) -> tuple[int, object]:
    """(niveau actuel, valeur suivante ou None si déjà au maximum) pour ce type d'amélioration."""
    field, ladder = BOOSTER_LADDERS[kind]
    if field in _AXIS_OF_FIELD:
        return _id_level(_AXIS_OF_FIELD[field], ladder, bonus.get(field))
    return _numeric_level(ladder, bonus.get(field))


def reroll_step(kind: str, token) -> tuple[int, object]:
    if kind == "reroll_guarantee":
        if token.reroll_mode == "random" and reroll_axes(token):
            return 0, "guaranteed_min"
        return 1, None
    if kind == "reroll_axis":
        axes = reroll_axes(token)
        missing = [a for a in AXES if a not in axes]
        return len(axes), (missing or None)
    if not reroll_axes(token):
        return 0, None  # reroll de puissance seule : pas de chances à booster
    return _numeric_level(REROLL_BOOSTS, token.reroll_boost)


def _cost_and_chance(cfg: dict, level: int, failures: int, event: dict | None) -> tuple[int, float]:
    m = cfg["machine"]
    cost = m["base_cost"] * m["level_cost_factor"] ** level * m["failure_cost_factor"] ** failures
    chance = m["base_chance"] * m["level_chance_factor"] ** level + m["failure_chance_step"] * failures
    if event:
        cost *= float(event.get("cost_factor", 1))
        chance += float(event.get("success_bonus", 0))
    return max(1, int(round(cost))), round(min(m["max_chance"], max(0.01, chance)), 3)


# ─────────────────────────────  RESSOURCES  ─────────────────────────────

def _resource_for(cfg: dict, kind: str, level: int) -> str | None:
    """Ressource liée à ce cran (niveau actuel 0 = premier cran) ; la dernière vaut pour la suite."""
    table = cfg["machine"]["resources"].get(kind) or []
    return table[min(level, len(table) - 1)] if table else None


def required_resource(cfg: dict, kind: str, level: int) -> dict | None:
    """Ressource obligatoire pour passer ce cran, ou None avant le cran de départ."""
    m = cfg["machine"]
    step = level + 1
    resource_id = _resource_for(cfg, kind, level)
    if step < m["resource_from_level"] or not resource_id:
        return None
    return {"resource_id": resource_id,
            "amount": int(m["resource_base_qty"] + m["resource_qty_step"] * (step - m["resource_from_level"]))}


def bonus_options(cfg: dict, kind: str) -> list[dict]:
    """Ressources qu'on peut ajouter à cette amélioration, et la réussite gagnée par unité."""
    per_unit = cfg["machine"]["bonus_per_unit"]
    ids = dict.fromkeys(cfg["machine"]["resources"].get(kind) or [])
    return [{"resource_id": r, "per_unit": float(per_unit[r])} for r in ids if per_unit.get(r)]


def bonus_cap(cfg: dict, level: int) -> float:
    caps = cfg["machine"]["bonus_caps"]
    return float(caps[min(level, len(caps) - 1)]) if caps else float(cfg["machine"]["max_chance"])


def chance_with_extra(cfg: dict, kind: str, level: int, chance: float, extra: dict[str, int]) -> float:
    """Réussite avec les ressources ajoutées : jamais au-delà du plafond du cran
    (mais jamais en dessous de la réussite sans ajout)."""
    per_unit = {o["resource_id"]: o["per_unit"] for o in bonus_options(cfg, kind)}
    bonus = sum(per_unit[r] * q for r, q in extra.items() if r in per_unit and q > 0)
    if bonus <= 0:
        return chance
    return round(max(chance, min(bonus_cap(cfg, level), chance + bonus)), 3)


async def _resource_names(session: AsyncSession) -> dict[str, str]:
    return {r.id: r.name for r in (await session.execute(select(Resource))).scalars().all()}


def _with_names(entry: dict | None, names: dict) -> dict | None:
    return {**entry, "name": names.get(entry["resource_id"], entry["resource_id"])} if entry else None


def _upgrade_out(cfg: dict, kind: str, level: int, nxt_label: str, cost: int, chance: float, res_names: dict) -> dict:
    return {
        "kind": kind, "label": KIND_LABEL[kind], "next": nxt_label, "level": level, "cost": cost, "chance": chance,
        "required": _with_names(required_resource(cfg, kind, level), res_names),
        "bonus_options": [_with_names(o, res_names) for o in bonus_options(cfg, kind)],
        "cap": bonus_cap(cfg, level),
    }


# ─────────────────────────────  LIBELLÉS  ─────────────────────────────

async def _names(session: AsyncSession) -> dict[str, str]:
    names = {}
    for model in (Rarity, Quality, Jewelry):
        for row in (await session.execute(select(model))).scalars().all():
            names[row.id] = row.name
    return names


def _fmt(v: float) -> str:
    return f"{v:g}".replace(".", ",")


def describe_bonus(bonus: dict, names: dict) -> str:
    bits = []
    if bonus.get("force_min_rarity_id"):
        bits.append(f"{names.get(bonus['force_min_rarity_id'], bonus['force_min_rarity_id'])} garantie")
    if bonus.get("rarity_weight_multiplier"):
        bits.append(f"rareté ×{_fmt(bonus['rarity_weight_multiplier'])}")
    if bonus.get("min_quality_id"):
        bits.append(f"qualité {names.get(bonus['min_quality_id'], bonus['min_quality_id'])} min.")
    if bonus.get("min_jewelry_id"):
        bits.append(f"bijou {names.get(bonus['min_jewelry_id'], bonus['min_jewelry_id'])} min.")
    if bonus.get("specialty_weight_multiplier"):
        bits.append(f"spécialité ×{_fmt(bonus['specialty_weight_multiplier'])}")
    if bonus.get("quality_weight_multiplier"):
        bits.append(f"qualité ×{_fmt(bonus['quality_weight_multiplier'])}")
    if bonus.get("jewelry_weight_multiplier"):
        bits.append(f"bijou ×{_fmt(bonus['jewelry_weight_multiplier'])}")
    if bonus.get("power_rolls"):
        bits.append(f"puissance ×{bonus['power_rolls']} tirages")
    return " · ".join(bits)


def describe_reroll(rules: dict) -> str:
    axes = [AXIS_LABEL[a] for a in AXES if rules.get(f"reroll_{a}")]
    label = "Reroll " + (" + ".join(axes) if axes else "puissance")
    label += " (garanti)" if rules.get("reroll_mode") == "guaranteed_min" else " (aléatoire)"
    if rules.get("reroll_boost"):
        label += f" · chances ×{_fmt(rules['reroll_boost'])}"
    return label


def _next_label(kind: str, nxt, names: dict) -> str:
    if kind in ("rarity_chances", "specialty_chances", "quality_chances", "jewelry_chances", "reroll_boost"):
        return f"chances ×{_fmt(nxt)}"
    if kind == "power_chances":
        return f"puissance tirée {nxt} fois, la meilleure gardée"
    if kind == "reroll_guarantee":
        return "mode garanti (égal ou mieux)"
    if kind == "reroll_axis":
        return "un axe de plus au hasard"
    return f"{names.get(nxt, nxt)} minimum" if kind != "rarity_guarantee" else f"{names.get(nxt, nxt)} garantie"


# ─────────────────────────────  ÉTAT  ─────────────────────────────

def _booster_bonus(owned: dict) -> dict:
    return {
        "force_min_rarity_id": owned.get("force_min_rarity_id"),
        "rarity_weight_multiplier": owned.get("rarity_weight_multiplier"),
        **{f: owned.get(f) for f in booster_inventory.EXTRA_BONUS_FIELDS},
    }


async def machine_state(session: AsyncSession, user: User) -> dict:
    cfg = await activities_config.get_config(session)
    plan = today_plan(cfg)
    row = await get_activity(session, user.id)
    failures = row.machine_failures or {}
    names = await _names(session)
    res_names = await _resource_names(session)
    items = []

    for owned in await booster_inventory.list_owned(session, user.id):
        bonus = _booster_bonus(owned)
        upgrades = []
        for kind in plan["kinds"]:
            if kind not in BOOSTER_LADDERS:
                continue
            level, nxt = booster_step(kind, bonus)
            if nxt is None:
                continue
            cost, chance = _cost_and_chance(cfg, level, failures.get(kind, 0), plan["event"])
            upgrades.append(_upgrade_out(cfg, kind, level, _next_label(kind, nxt, names), cost, chance, res_names))
        items.append({
            "item": "booster", "booster_id": owned["booster_id"], "bonus_id": owned["bonus_id"],
            "name": owned["booster_name"], "detail": describe_bonus(bonus, names) or "sans bonus",
            "quantity": owned["quantity"], "upgrades": upgrades,
        })

    tokens = (await session.execute(
        select(UserRerollToken).where(UserRerollToken.user_id == user.id, UserRerollToken.quantity > 0)
        .order_by(UserRerollToken.id)
    )).scalars().all()
    for token in tokens:
        upgrades = []
        for kind in plan["kinds"]:
            if kind not in REROLL_KINDS:
                continue
            level, nxt = reroll_step(kind, token)
            if nxt is None:
                continue
            cost, chance = _cost_and_chance(cfg, level, failures.get(kind, 0), plan["event"])
            label = _next_label(kind, nxt[0] if isinstance(nxt, list) else nxt, names)
            upgrades.append(_upgrade_out(cfg, kind, level, label, cost, chance, res_names))
        items.append({
            "item": "reroll", "token_id": token.id, "name": token.label or "Reroll",
            "detail": describe_reroll(reroll_inventory.rules_of(token)), "quantity": token.quantity, "upgrades": upgrades,
        })

    return {
        "day": plan["day"],
        "length": plan["length"],
        "today": [{"kind": k, "label": KIND_LABEL[k]} for k in plan["kinds"]],
        "event": {"id": plan["event"]["id"], "label": plan["event"]["label"]} if plan["event"] else None,
        # Contenu du cycle (sans l'ordre : on ne sait pas quand tombent les événements).
        "cycle_upgrades": [KIND_LABEL[k] for k in cfg["machine"]["cycle_upgrades"] if k in KIND_LABEL],
        "cycle_events": [e["label"] for e in cfg["machine"]["events"]],
        "items": items,
    }


# ─────────────────────────────  AMÉLIORATION  ─────────────────────────────

async def upgrade(session: AsyncSession, user: User, item: str, kind: str, booster_id: str | None = None,
                  bonus_id: int | None = None, token_id: int | None = None,
                  extra: dict[str, int] | None = None) -> dict:
    cfg = await activities_config.get_config(session)
    plan = today_plan(cfg)
    if kind not in plan["kinds"]:
        raise HTTPException(400, "Cette amélioration n'est pas disponible aujourd'hui.")
    row = await get_activity(session, user.id)
    failures = dict(row.machine_failures or {})
    names = await _names(session)
    event = plan["event"]

    # Objet ciblé et amélioration visée.
    if item == "booster":
        if kind not in BOOSTER_LADDERS or not booster_id:
            raise HTTPException(400, "Amélioration invalide pour un booster.")
        if bonus_id is not None:
            source = await session.get(UserBonusBooster, bonus_id, **booster_inventory.LOCKED)
            if not source or source.user_id != user.id or source.booster_id != booster_id or source.quantity < 1:
                raise HTTPException(400, "Tu ne possèdes plus ce booster.")
            bonus = {"force_min_rarity_id": source.force_min_rarity_id,
                     "rarity_weight_multiplier": source.rarity_weight_multiplier,
                     **booster_inventory.extra_bonus(source)}
        else:
            source = await session.get(UserBoosterInventory, (user.id, booster_id), **booster_inventory.LOCKED)
            if not source or source.quantity < 1:
                raise HTTPException(400, "Tu ne possèdes plus ce booster.")
            bonus = {"force_min_rarity_id": None, "rarity_weight_multiplier": None,
                     **{f: None for f in booster_inventory.EXTRA_BONUS_FIELDS}}
        level, nxt = booster_step(kind, bonus)
    elif item == "reroll":
        if kind not in REROLL_KINDS or token_id is None:
            raise HTTPException(400, "Amélioration invalide pour un reroll.")
        source = await session.get(UserRerollToken, token_id, **booster_inventory.LOCKED)
        if not source or source.user_id != user.id or source.quantity < 1:
            raise HTTPException(400, "Tu ne possèdes plus ce reroll.")
        level, nxt = reroll_step(kind, source)
    else:
        raise HTTPException(400, "Objet invalide.")
    if nxt is None:
        raise HTTPException(400, "Cet objet est déjà au maximum pour cette amélioration.")

    cost, chance = _cost_and_chance(cfg, level, failures.get(kind, 0), event)
    # Ressources ajoutées : seulement celles liées à l'amélioration, quantités bornées.
    allowed = {o["resource_id"] for o in bonus_options(cfg, kind)}
    extra = {r: int(q) for r, q in (extra or {}).items() if int(q) > 0}
    if any(r not in allowed or q > MAX_EXTRA_PER_RESOURCE for r, q in extra.items()):
        raise HTTPException(400, "Ressource ajoutée invalide pour cette amélioration.")
    chance = chance_with_extra(cfg, kind, level, chance, extra)
    required = required_resource(cfg, kind, level)
    spend = {"coins": cost}
    if required:
        spend[required["resource_id"]] = required["amount"]
    for res_id, qty in extra.items():
        spend[res_id] = spend.get(res_id, 0) + qty
    for res_id, qty in spend.items():
        await require_balance(session, user, res_id, qty)
    for res_id, qty in spend.items():
        await apply_delta(session, user, res_id, -qty)

    roll = random.random()
    success = roll < chance
    destroyed = False
    result_label = None
    if success:
        failures[kind] = 0
        source.quantity -= 1
        session.add(source)
        if item == "booster":
            field = BOOSTER_LADDERS[kind][0]
            bonus[field] = nxt
            booster = await session.get(Booster, booster_id)
            description = describe_bonus(bonus, names)
            await booster_inventory.grant_bonus(
                session, user.id, booster_id, bonus["force_min_rarity_id"], bonus["rarity_weight_multiplier"],
                (description[:1].upper() + description[1:])[:100], 1,
                extras={f: bonus[f] for f in booster_inventory.EXTRA_BONUS_FIELDS},
            )
            result_label = f"{booster.name if booster else booster_id} ({description})"
        else:
            rules = reroll_inventory.rules_of(source)
            if kind == "reroll_guarantee":
                rules["reroll_mode"] = "guaranteed_min"
            elif kind == "reroll_axis":
                rules[f"reroll_{random.choice(nxt)}"] = True
                rules["reroll_mode"] = rules.get("reroll_mode") or "random"
            else:
                rules["reroll_boost"] = nxt
            result_label = describe_reroll(rules)
            await reroll_inventory.grant_rules(session, user.id, None, result_label[:100], rules, 1)
    else:
        failures[kind] = failures.get(kind, 0) + 1
        if event and event.get("lose_on_fail"):
            destroyed = True
            source.quantity -= 1
            session.add(source)

    row.machine_failures = failures
    session.add(row)
    await session.commit()
    # Trace de chaque essai (vérification des chances en production).
    logger.info("Machine : joueur %s, %s %s, cran %s, chance %.3f, tirage %.3f, dépense %s -> %s%s",
                user.id, item, kind, level + 1, chance, roll, spend,
                "réussi" if success else "raté", " (objet détruit)" if destroyed else "")
    return {"success": success, "destroyed": destroyed, "cost": cost, "chance": chance, "result": result_label,
            "spent": spend, "state": await machine_state(session, user)}


# ─────────────────────────────  CONVERTISSEUR  ─────────────────────────────

def _roll_converter_day(row) -> None:
    today = datetime.utcnow().date()
    if row.converter_day != today:
        row.converter_day = today
        row.converter_uses = 0


async def converter_state(session: AsyncSession, user: User) -> dict:
    full_cfg = await activities_config.get_config(session)
    cfg = full_cfg["converter"]
    row = await get_activity(session, user.id)
    _roll_converter_day(row)
    session.add(row)
    await session.commit()
    uses = unlocks.converter_uses(full_cfg, await unlocks.level_of(session, user))
    return {"daily_uses": uses, "uses_left": max(0, uses - row.converter_uses), "pairs": cfg["pairs"]}


async def convert(session: AsyncSession, user: User, from_id: str, to_id: str, amount: int) -> dict:
    full_cfg = await activities_config.get_config(session)
    cfg = full_cfg["converter"]
    pair = next((p for p in cfg["pairs"] if p["from"] == from_id and p["to"] == to_id), None)
    if not pair:
        raise HTTPException(400, "Conversion indisponible.")
    row = await get_activity(session, user.id)
    _roll_converter_day(row)
    if row.converter_uses >= unlocks.converter_uses(full_cfg, await unlocks.level_of(session, user)):
        raise HTTPException(400, "Plus de conversions disponibles aujourd'hui.")
    give, get = int(pair["give"]), int(pair["get"])
    if amount < give or amount % give:
        raise HTTPException(400, f"Montant en multiples de {give}.")
    if amount > int(pair["max_in"]):
        raise HTTPException(400, f"{pair['max_in']} au maximum par conversion.")
    await require_balance(session, user, from_id, amount)
    gained = amount // give * get
    await apply_delta(session, user, from_id, -amount)
    await apply_delta(session, user, to_id, gained)
    row.converter_uses += 1
    session.add(row)
    await session.commit()
    return {"spent": amount, "gained": gained, "state": await converter_state(session, user)}
