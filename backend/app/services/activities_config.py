"""
Réglages des activités (présence, coffre, expéditions, atelier, mini-jeux),
éditables depuis l'admin. Stockés en JSON dans GameConfig.activities et
fusionnés avec les valeurs par défaut ci-dessous : une clé absente en base
reprend toujours sa valeur par défaut.
"""

import copy

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game_config import GameConfig
from app.services import resource_catalog

DEFAULTS: dict = {
    # Booster utilisé pour les récompenses (atelier, expéditions, roue).
    "reward_booster_id": "booster_A1",
    "presence": {
        "max_multiplier": 1.5,     # bonus de chance au maximum (tous axes)
        "full_after_hours": 8,     # temps de présence continue pour l'atteindre
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
    # Niveau (plus haut atteint) qui débloque chaque fonctionnalité (cf. services/unlocks.py).
    "unlocks": {
        "workshop": 2, "absence_chest": 2, "leaderboard": 2,
        "expeditions": 3, "resource_shop": 3, "showcase": 3,
        "gifts": 4, "wheel": 4,
        "trades": 5, "guild_join": 5, "presence_luck": 5,
        "higher_lower": 6, "rerolls": 6,
        "listings": 7, "converter": 7,
        "machine": 8, "guild_create": 8,
    },
    # Progressions liées au niveau : tables {"niveau": valeur} ou base + per_level (plafonné).
    "progression": {
        "expedition_slots": {"3": 1, "9": 2, "14": 3},
        "workshop_gauges": {"base": 10, "per_level": 2, "max": 40},
        "presence_max": {"base": 1.2, "per_level": 0.03, "max": 1.5},
        "higher_lower_max_stake": {"base": 500, "per_level": 500, "max": 5000},
        "converter_uses": {"7": 1, "12": 2, "17": 3},
    },
    # Classement : le meilleur rang (et les succès « top N ») n'est retenu qu'à
    # partir de ce nombre de joueurs classés — sinon être premier serait automatique.
    "ranking": {"min_players": 10},
    # Défi du mois (cf. services/monthly.py) : tranches de récompenses, de la
    # meilleure à la plus large ; chaque joueur reçoit la première atteinte.
    # Une tranche : "rank" (jusqu'à ce rang), "top_pct" (meilleurs X %) ou
    # "min_points" (participation). Guilde : chaque membre reçoit la récompense.
    "monthly": {
        "solo_rewards": [
            {"label": "1re place", "rank": 1, "rewards": [{"kind": "resource", "id": "coins", "amount": 20000}, {"kind": "resource", "id": "frag_legendary", "amount": 10}, {"kind": "resource", "id": "dust_star", "amount": 10}]},
            {"label": "2e place", "rank": 2, "rewards": [{"kind": "resource", "id": "coins", "amount": 12000}, {"kind": "resource", "id": "frag_legendary", "amount": 6}]},
            {"label": "3e place", "rank": 3, "rewards": [{"kind": "resource", "id": "coins", "amount": 8000}, {"kind": "resource", "id": "frag_legendary", "amount": 4}]},
            {"label": "Top 10", "rank": 10, "rewards": [{"kind": "resource", "id": "coins", "amount": 4000}, {"kind": "resource", "id": "frag_epic", "amount": 5}]},
            {"label": "Top 25 %", "top_pct": 25, "rewards": [{"kind": "resource", "id": "coins", "amount": 2000}, {"kind": "resource", "id": "frag_rare", "amount": 5}]},
            {"label": "Participation", "min_points": 1, "rewards": [{"kind": "resource", "id": "coins", "amount": 500}]},
        ],
        "guild_rewards": [
            {"label": "1re", "rank": 1, "rewards": [{"kind": "resource", "id": "coins", "amount": 5000}, {"kind": "resource", "id": "frag_epic", "amount": 5}]},
            {"label": "2e", "rank": 2, "rewards": [{"kind": "resource", "id": "coins", "amount": 3000}, {"kind": "resource", "id": "frag_epic", "amount": 3}]},
            {"label": "3e", "rank": 3, "rewards": [{"kind": "resource", "id": "coins", "amount": 2000}, {"kind": "resource", "id": "frag_rare", "amount": 5}]},
        ],
    },
    # Prestige : niveaux au-delà de la route. Chacun demande power_growth de
    # puissance en plus du précédent et rapporte la récompense du dernier palier
    # majorée de reward_growth par prestige, plus un bonus.
    "prestige": {"power_growth": 0.25, "reward_growth": 0.10, "bonus_resource_id": "frag_legendary", "bonus_amount": 1},
    # Écart de niveau maximum pour un transfert entre joueurs — échange, achat
    # d'annonce, cadeau (cf. services/level_gap.py). Proportionnel au plus haut
    # des deux niveaux, avec un plancher pour le début de jeu.
    "level_gap": {"ratio": 0.30, "min_gap": 5},
    # Taxe sur les transferts entre joueurs (cf. services/trade_tax.py).
    "trade_tax": {
        "base_rate": 0.05, "per_level": 0.01, "max_rate": 0.25,
        "card_anchor": 4, "card_exponent": 1.15, "card_cap": 3000,
        "resource_values": {"dust": 5, **resource_catalog.coin_values()},
        "booster_value": 100, "reroll_value": 300,
    },
    # Machine d'amélioration : cycle de N jours (une amélioration par jour + les
    # jours d'événement), dans un ordre tiré au hasard à chaque nouveau cycle
    # (le même pour tout le monde). Un jour d'événement propose une amélioration
    # tirée au hasard, avec l'effet de l'événement.
    "machine": {
        "cycle_start": "2026-09-21",
        "cycle_upgrades": [
            "rarity_chances", "rarity_guarantee", "quality_chances", "quality_guarantee",
            "jewelry_chances", "jewelry_guarantee", "specialty_chances", "power_chances",
            "reroll_axis", "reroll_boost", "reroll_guarantee",
        ],
        "events": [
            {"id": "risky", "label": "Jour risqué : -60 % sur le prix, mais un échec détruit l'objet",
             "cost_factor": 0.4, "success_bonus": 0, "lose_on_fail": True},
            {"id": "sale", "label": "Soldes : -50 % sur le prix", "cost_factor": 0.5,
             "success_bonus": 0, "lose_on_fail": False},
            {"id": "lucky", "label": "Jour de chance : +15 % de réussite", "cost_factor": 1,
             "success_bonus": 0.15, "lose_on_fail": False},
        ],
        "base_cost": 400,
        "level_cost_factor": 1.8,
        "failure_cost_factor": 1.25,
        "base_chance": 0.35,
        "level_chance_factor": 0.7,
        "failure_chance_step": 0.05,
        "max_chance": 0.9,
        # Ressources : obligatoires à partir d'un cran (quantité base + pas × crans
        # au-delà), et facultatives dès le premier cran pour réduire le risque
        # d'échec. Ressource demandée par cran (la dernière vaut pour les suivants).
        "resource_from_level": 3,
        "resource_base_qty": 2,
        "resource_qty_step": 2,
        "resources": {
            "rarity_chances": ["frag_rare", "frag_rare", "frag_epic", "frag_legendary"],
            "rarity_guarantee": ["frag_rare", "frag_epic", "frag_legendary"],
            "quality_guarantee": ["dust_lustrous", "dust_lustrous", "dust_pearly", "dust_pearly", "dust_star"],
            "jewelry_guarantee": ["silver_ore", "gold_nugget", "rough_diamond", "prism_crystal"],
            "specialty_chances": ["art_ink", "art_ink", "ex_seal", "glitter"],
            "quality_chances": ["dust_fine", "dust_lustrous", "dust_pearly", "dust_star"],
            "jewelry_chances": ["silver_ore", "gold_nugget", "rough_diamond", "prism_crystal"],
            "power_chances": ["dust_fine", "dust_lustrous", "dust_pearly", "dust_star"],
            "reroll_guarantee": ["dust_pearly"],
            "reroll_axis": ["dust_fine", "dust_lustrous", "dust_pearly", "dust_star"],
            "reroll_boost": ["dust_lustrous", "dust_pearly", "dust_star"],
        },
        # Réussite ajoutée par unité de ressource ajoutée volontairement (plus la
        # ressource est rare, plus elle aide), dans la limite du plafond du cran :
        # un cran élevé n'est jamais garanti.
        "bonus_per_unit": {
            "frag_rare": 0.02, "frag_epic": 0.05, "frag_legendary": 0.12,
            "silver_ore": 0.02, "gold_nugget": 0.04, "rough_diamond": 0.08, "prism_crystal": 0.15,
            "art_ink": 0.03, "ex_seal": 0.06, "glitter": 0.10,
            "dust_fine": 0.01, "dust_lustrous": 0.03, "dust_pearly": 0.06, "dust_star": 0.12,
        },
        "bonus_caps": [1.0, 0.85, 0.70, 0.55, 0.40],
    },
    # Convertisseur : un nombre d'utilisations par jour, une quantité maximale
    # par conversion ; `give` de la ressource de départ donnent `get` de l'autre.
    "converter": {
        "daily_uses": 3,
        "pairs": [
            {"from": "coins", "to": "dust", "give": 10, "get": 1, "max_in": 2000},
            {"from": "dust", "to": "coins", "give": 1, "get": 5, "max_in": 200},
            *resource_catalog.converter_pairs(),
        ],
    },
    # Recyclage : poussière pour toute carte (plage selon sa rareté), plus une
    # ressource par palier atteint sur chaque caractéristique. La quantité se
    # place dans la plage [min, max] selon la puissance de la carte rapportée
    # à SON maximum (un très bon tirage rapporte le maximum).
    "recycling": {
        # Fourchette de tirage autour de la cible donnée par la puissance (0,3 = ± 30 %).
        "spread": 0.3,
        "dust_by_rarity": {"common": [1, 5], "rare": [5, 30], "epic": [20, 150], "legendary": [100, 1000]},
        "rarity": {"rare": "frag_rare", "epic": "frag_epic", "legendary": "frag_legendary"},
        "jewelry": {"silver": "silver_ore", "gold": "gold_nugget", "diamond": "rough_diamond",
                    "prismatic": "prism_crystal"},
        "specialty": {"full_art": "art_ink", "ex": "ex_seal", "shiny": "glitter"},
        "quality": {"faded": "dust_fine", "worn": "dust_fine", "fair": "dust_fine",
                    "preserved": "dust_lustrous", "excellent": "dust_lustrous",
                    "graded": "dust_pearly", "mint": "dust_pearly", "authentic": "dust_star"},
        "ranges": {
            "frag_rare": [1, 3], "frag_epic": [1, 5], "frag_legendary": [1, 10],
            "silver_ore": [1, 3], "gold_nugget": [1, 5], "rough_diamond": [1, 8], "prism_crystal": [1, 15],
            "art_ink": [1, 3], "ex_seal": [1, 5], "glitter": [1, 8],
            "dust_fine": [1, 5], "dust_lustrous": [1, 5], "dust_pearly": [1, 8], "dust_star": [1, 15],
        },
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
