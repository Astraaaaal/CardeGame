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
    "guilds": {
        "creation_cost": 2000,
        "base_members": 20,
        "members_by_level": {"5": 25, "10": 30},
        "leave_cooldown_hours": 4,
        "xp_per_level": 1000,           # niveau L à 1000 × L(L−1)/2 XP
        "points_per_coins": 10,         # 10 pièces données = 1 point de coffre (et 1 XP)
        "points_per_dust": 2,
        "daily_bonus_per_level_pct": 2,  # +2 % de récompense du jour par niveau
        "daily_bonus_cap_pct": 20,
        "expedition_slot_level": 5,     # +1 emplacement d'expédition à ce niveau
        # Objectif hebdomadaire : quantité par membre au palier 1, +25 % par palier.
        "tier_step": 0.25,
        "objectives": {
            "packs_opened": 8, "cards_recycled": 15, "trades_completed": 1,
            "expeditions_completed": 4, "workshop_gauges": 20, "quests_completed": 5,
            "rare_cards_obtained": 6,
        },
        "objective_labels": {
            "packs_opened": "Ouvrir des boosters", "cards_recycled": "Recycler des cartes",
            "trades_completed": "Conclure des échanges", "expeditions_completed": "Terminer des expéditions",
            "workshop_gauges": "Remplir des jauges d'atelier", "quests_completed": "Terminer des quêtes",
            "rare_cards_obtained": "Obtenir des cartes rares",
        },
        "objective_xp": 300,     # XP de guilde par objectif réussi (× palier)
        "objective_coins": 150,  # récompense de chaque contributeur (× palier)
        "objective_dust": 30,
        "buffs": {
            "luck": {"label": "Chance ×1,5 (48 h)", "cost": 500, "hours": 48, "value": 1.5},
            "expedition_loot": {"label": "+25 % de butin d'expédition (7 j)", "cost": 400, "hours": 168, "value": 1.25},
            "daily_reward": {"label": "+20 % à la récompense du jour (7 j)", "cost": 300, "hours": 168, "value": 1.2},
            "workshop": {"label": "+10 jauges d'atelier par jour (7 j)", "cost": 300, "hours": 168, "value": 10},
        },
    },
    # Gain de chaque bonne réponse = (1 - marge) × (1 - P(égalité)) / P(réussite),
    # plafonné ; encaissement possible à partir de `min_cashout_step` manches.
    "higher_lower": {"min_stake": 50, "max_stake": 5000, "max_steps": 10, "house_edge": 0.02,
                     "min_cashout_step": 3, "max_step_multiplier": 20},
    # Machine d'amélioration : l'amélioration du jour suit la rotation (0 = lundi),
    # avec parfois un événement aléatoire (identique pour tous ce jour-là).
    "machine": {
        "rotation": {
            "0": ["rarity_chances"], "1": ["rarity_guarantee"], "2": ["quality_guarantee"],
            "3": ["jewelry_guarantee"], "4": ["specialty_chances"], "5": ["reroll_axis", "reroll_boost"],
            "6": ["reroll_guarantee"],
        },
        "events": [
            {"id": "risky", "label": "Jour risqué : -60 % sur le prix, mais un échec détruit l'objet",
             "chance": 0.08, "cost_factor": 0.4, "success_bonus": 0, "lose_on_fail": True},
            {"id": "sale", "label": "Soldes : -50 % sur le prix", "chance": 0.07, "cost_factor": 0.5,
             "success_bonus": 0, "lose_on_fail": False},
            {"id": "lucky", "label": "Jour de chance : +15 % de réussite", "chance": 0.05, "cost_factor": 1,
             "success_bonus": 0.15, "lose_on_fail": False},
        ],
        "base_cost": 400,
        "level_cost_factor": 1.8,
        "failure_cost_factor": 1.25,
        "base_chance": 0.35,
        "level_chance_factor": 0.7,
        "failure_chance_step": 0.05,
        "max_chance": 0.9,
    },
    # Convertisseur : un nombre d'utilisations par jour, une quantité maximale
    # par conversion ; `give` de la ressource de départ donnent `get` de l'autre.
    "converter": {
        "daily_uses": 3,
        "pairs": [
            {"from": "coins", "to": "dust", "give": 10, "get": 1, "max_in": 2000},
            {"from": "dust", "to": "coins", "give": 1, "get": 5, "max_in": 200},
        ],
    },
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
