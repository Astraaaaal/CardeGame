"""
Réglages des activités (présence, coffre, expéditions, atelier, mini-jeux),
éditables depuis l'admin. Stockés en JSON dans GameConfig.activities et
fusionnés avec les valeurs par défaut ci-dessous : une clé absente en base
reprend toujours sa valeur par défaut.
"""

import copy

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game_config import GameConfig

DEFAULTS: dict = {
    # Booster utilisé pour les récompenses (atelier, expéditions, roue).
    "reward_booster_id": "booster_A1",
    "presence": {
        "max_multiplier": 2.5,     # chance de rareté au maximum
        "full_after_hours": 5,     # temps de présence continue pour l'atteindre
        "reset_after_minutes": 5,  # absence qui remet le bonus à zéro
    },
    "chest": {"coins_per_hour": 100, "dust_per_hour": 20, "cap_hours": 12},
    "expeditions": {
        "slots": 3,
        "max_cards": 3,
        "durations": [15, 60, 240, 480],
        "coins_per_minute": 2,
        "dust_ratio": 0.2,
        # Puissance cumulée qui double le butin ; bonus plafonné à ×3.
        "power_scale": 5000,
        "max_power_factor": 3,
        "booster_chance": {"15": 0.02, "60": 0.06, "240": 0.2, "480": 0.35},
        "rare_card_chance": {"15": 0.0, "60": 0.01, "240": 0.03, "480": 0.06},
    },
    "workshop": {
        "taps_per_gauge": 100,
        "max_taps_per_second": 10,
        "coins_per_gauge": 50,
        "dust_chance": 0.05,
        "dust_amount": 20,
        "fragments_per_booster": 10,
        "gauges_per_day": 20,
    },
    "higher_lower": {"min_stake": 50, "max_stake": 5000, "multiplier": 1.8, "max_steps": 10},
    "wheel": {
        "extra_spin_cost": 200,
        "extra_spins_per_day": 5,
        "segments": [
            {"label": "100 pièces", "kind": "resource", "id": "coins", "amount": 100, "weight": 30},
            {"label": "50 poussière", "kind": "resource", "id": "dust", "amount": 50, "weight": 20},
            {"label": "300 pièces", "kind": "resource", "id": "coins", "amount": 300, "weight": 15},
            {"label": "Booster", "kind": "booster", "id": "", "amount": 1, "weight": 8},
            {"label": "150 poussière", "kind": "resource", "id": "dust", "amount": 150, "weight": 10},
            {"label": "Reroll", "kind": "reroll", "id": "", "amount": 1, "weight": 7},
            {"label": "1 000 pièces", "kind": "resource", "id": "coins", "amount": 1000, "weight": 8},
            {"label": "Jackpot", "kind": "resource", "id": "coins", "amount": 5000, "weight": 2},
        ],
    },
}


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


async def get_config(session: AsyncSession) -> dict:
    config = await session.get(GameConfig, 1)
    return _merge(DEFAULTS, (config.activities if config else None) or {})


async def save_config(session: AsyncSession, values: dict) -> dict:
    """Enregistre les réglages (fusionnés avec les défauts). Ne valide que la forme."""
    config = await session.get(GameConfig, 1)
    if not config:
        config = GameConfig()
    merged = _merge(DEFAULTS, values)
    config.activities = merged
    session.add(config)
    await session.commit()
    return merged
