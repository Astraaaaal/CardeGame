"""
Déblocage des fonctionnalités par niveau, et progressions liées au niveau.

On retient le plus haut niveau jamais atteint (User.max_level) : une
fonctionnalité débloquée le reste même si la puissance baisse ensuite
(recyclage, échange…). Niveaux et progressions réglables dans l'admin
(sections « unlocks » et « progression » des réglages d'activités).
"""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services import activities_config
from app.services.levels import current_level_for_power, get_all_tiers, get_total_power

FEATURE_LABELS = {
    "workshop": "Atelier",
    "absence_chest": "Coffre d'absence",
    "leaderboard": "Classement",
    "expeditions": "Expéditions",
    "resource_shop": "Boutique Ressources",
    "gifts": "Cadeaux",
    "wheel": "Roue de la fortune",
    "trades": "Échanges",
    "guild_join": "Rejoindre une guilde",
    "presence_luck": "Chance de présence",
    "higher_lower": "Plus ou moins",
    "rerolls": "Rerolls",
    "listings": "Annonces « à échanger »",
    "converter": "Convertisseur",
    "machine": "Machine d'amélioration",
    "guild_create": "Fonder une guilde",
}


async def level_of(session: AsyncSession, user: User) -> int:
    """Plus haut niveau atteint (mis à jour si la puissance actuelle fait mieux). Ne commit pas."""
    tiers = await get_all_tiers(session)
    current = current_level_for_power(tiers, await get_total_power(session, user.id)) if tiers else 1
    if current > (user.max_level or 1):
        user.max_level = current
        session.add(user)
    return max(user.max_level or 1, current)


def required_level(cfg: dict, feature: str) -> int:
    return int(cfg["unlocks"].get(feature, 1))


async def require(session: AsyncSession, user: User, feature: str) -> None:
    """403 si la fonctionnalité n'est pas encore débloquée pour ce joueur."""
    cfg = await activities_config.get_config(session)
    needed = required_level(cfg, feature)
    if needed > 1 and await level_of(session, user) < needed:
        raise HTTPException(403, f"{FEATURE_LABELS.get(feature, 'Cette fonctionnalité')} se débloque au niveau {needed}.")


async def is_unlocked(session: AsyncSession, user: User, feature: str) -> bool:
    cfg = await activities_config.get_config(session)
    return await level_of(session, user) >= required_level(cfg, feature)


# ─────────────────────────────  PROGRESSIONS  ─────────────────────────────

def _steps(table: dict, level: int, default: int = 0) -> int:
    """Valeur du plus haut palier atteint dans une table {"niveau": valeur}."""
    value = default
    for lvl, v in sorted(((int(k), v) for k, v in table.items()), key=lambda kv: kv[0]):
        if level >= lvl:
            value = v
    return value


def _linear(spec: dict, level: int, unlock_level: int) -> float:
    """base au niveau de déblocage, + per_level par niveau au-delà, plafonné à max."""
    if level < unlock_level:
        return 0
    return min(spec["max"], spec["base"] + spec["per_level"] * (level - unlock_level))


def expedition_slots(cfg: dict, level: int) -> int:
    return _steps(cfg["progression"]["expedition_slots"], level)


def workshop_gauges(cfg: dict, level: int) -> int:
    return int(_linear(cfg["progression"]["workshop_gauges"], level, required_level(cfg, "workshop")))


def presence_max_multiplier(cfg: dict, level: int) -> float:
    value = _linear(cfg["progression"]["presence_max"], level, required_level(cfg, "presence_luck"))
    return round(value, 2) if value else 1.0


def higher_lower_max_stake(cfg: dict, level: int) -> int:
    return int(_linear(cfg["progression"]["higher_lower_max_stake"], level, required_level(cfg, "higher_lower")))


def converter_uses(cfg: dict, level: int) -> int:
    return _steps(cfg["progression"]["converter_uses"], level)


async def status(session: AsyncSession, user: User) -> dict:
    """Niveau retenu, fonctionnalités et paliers de déblocage (pour l'interface)."""
    cfg = await activities_config.get_config(session)
    level = await level_of(session, user)
    await session.commit()
    return {
        "level": level,
        "features": {
            key: {"label": label, "level": required_level(cfg, key), "unlocked": level >= required_level(cfg, key)}
            for key, label in FEATURE_LABELS.items()
        },
    }
