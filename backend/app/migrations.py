"""
Petits correctifs de schéma et de données, idempotents, appliqués au démarrage
juste après `SQLModel.metadata.create_all` (qui ne crée que les tables
manquantes — pas les colonnes ajoutées sur une table déjà existante).

Chaque étape doit pouvoir être rejouée sans risque à chaque démarrage.
"""

import copy
import logging

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.services.activities_config import DEFAULTS as ACTIVITIES_DEFAULTS
from app.services.power import power_range, roll_power
from app.services.resource_catalog import NEW_RESOURCES, converter_pairs

logger = logging.getLogger(__name__)

_STATEMENTS = [
    # Provenance d'une carte : quel booster l'a produite.
    "ALTER TABLE user_cards ADD COLUMN IF NOT EXISTS booster_id VARCHAR(30)",
    # Un booster peut piocher dans plusieurs sets (table de liaison) ; on
    # rattache les boosters existants à leur set d'origine pour ne rien casser.
    "INSERT INTO booster_sets (booster_id, set_id) "
    "SELECT id, set_id FROM boosters "
    "ON CONFLICT DO NOTHING",
    # Valeur de recyclage par axe (rareté / qualité / spécialité / jewelry).
    "ALTER TABLE rarities ADD COLUMN IF NOT EXISTS recycle_value INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE qualities ADD COLUMN IF NOT EXISTS recycle_value INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE specialties ADD COLUMN IF NOT EXISTS recycle_value INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE jewelries ADD COLUMN IF NOT EXISTS recycle_value INTEGER NOT NULL DEFAULT 0",
    # recycle_value n'est plus utilisé (recyclage : réglages « recycling ») ; la
    # colonne reste, avec une valeur par défaut pour les insertions qui l'ignorent.
    "ALTER TABLE characters ADD COLUMN IF NOT EXISTS full_art BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE characters ADD COLUMN IF NOT EXISTS full_art_image_url VARCHAR(300) NOT NULL DEFAULT ''",
    "ALTER TABLE rarities ALTER COLUMN recycle_value SET DEFAULT 0",
    "ALTER TABLE qualities ALTER COLUMN recycle_value SET DEFAULT 0",
    "ALTER TABLE specialties ALTER COLUMN recycle_value SET DEFAULT 0",
    "ALTER TABLE jewelries ALTER COLUMN recycle_value SET DEFAULT 0",
    # Interrupteurs de visibilité/activation d'un booster.
    "ALTER TABLE boosters ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE boosters ADD COLUMN IF NOT EXISTS visible_in_shop BOOLEAN NOT NULL DEFAULT TRUE",
    # Rationnement d'achat + rotation quotidienne + override de probas booster.
    "ALTER TABLE shop_offers ADD COLUMN IF NOT EXISTS purchase_limit_per_day INTEGER",
    "ALTER TABLE shop_offers ADD COLUMN IF NOT EXISTS is_daily_pool BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE shop_offers ADD COLUMN IF NOT EXISTS force_min_rarity_id VARCHAR(20)",
    "ALTER TABLE shop_offers ADD COLUMN IF NOT EXISTS rarity_weight_multiplier DOUBLE PRECISION",
    # Reroll : axes concernés + mode.
    "ALTER TABLE shop_offers ADD COLUMN IF NOT EXISTS reroll_rarity BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE shop_offers ADD COLUMN IF NOT EXISTS reroll_quality BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE shop_offers ADD COLUMN IF NOT EXISTS reroll_specialty BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE shop_offers ADD COLUMN IF NOT EXISTS reroll_jewelry BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE shop_offers ADD COLUMN IF NOT EXISTS reroll_mode VARCHAR(20)",
    # Ressource système non supprimable (ex: "coins").
    "ALTER TABLE resources ADD COLUMN IF NOT EXISTS protected BOOLEAN NOT NULL DEFAULT FALSE",
    # Monnaie utilisée par un booster à l'achat classique (permet de vendre
    # un booster contre une ressource autre que les pièces).
    "ALTER TABLE boosters ADD COLUMN IF NOT EXISTS resource_id VARCHAR(30) NOT NULL DEFAULT 'coins'",
    # Retrait du kind "upgrade" (initiative non demandée, redondante avec
    # reroll en mode garanti). Nettoie les offres orphelines avant de retirer
    # les colonnes qui n'étaient utilisées que par ce kind.
    "DELETE FROM shop_purchases WHERE offer_id IN (SELECT id FROM shop_offers WHERE kind = 'upgrade')",
    "DELETE FROM daily_features WHERE offer_id IN (SELECT id FROM shop_offers WHERE kind = 'upgrade')",
    "DELETE FROM shop_offers WHERE kind = 'upgrade'",
    "ALTER TABLE shop_offers DROP COLUMN IF EXISTS target_quality_id",
    "ALTER TABLE shop_offers DROP COLUMN IF EXISTS target_specialty_id",
    # Statut "en ligne" approximatif (cf. core/dependencies.py).
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP",
    # Vitrine publique : avatar (personnage possédé) + jusqu'à 3 cartes mises en avant.
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_character_id VARCHAR(30)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS showcase_card_1_id VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS showcase_card_2_id VARCHAR",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS showcase_card_3_id VARCHAR",
    # Couverture personnalisée d'un booster (remplace le visuel générique).
    "ALTER TABLE boosters ADD COLUMN IF NOT EXISTS cover_image_url VARCHAR(300) NOT NULL DEFAULT ''",
    # Paramètres sociaux : qui peut envoyer une demande d'ami / d'échange, popup de notif.
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS allow_friend_requests BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS trade_request_policy VARCHAR(20) NOT NULL DEFAULT 'friends'",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS trade_request_popup_enabled BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE trade_requests ADD COLUMN IF NOT EXISTS seen BOOLEAN NOT NULL DEFAULT FALSE",
    # Puissance d'une carte (cf. app/services/power.py) — tirée au hasard à
    # l'obtention, backfillée ci-dessous pour les cartes déjà en base.
    "ALTER TABLE user_cards ADD COLUMN IF NOT EXISTS power INTEGER",
    # Session d'échange en direct : la FK carte -> user_cards ne doit PAS
    # bloquer la suppression d'une carte référencée par un item (recyclage
    # d'une carte qui a un jour fait partie d'un échange, même terminé) —
    # sans ceci, un simple recyclage peut planter avec une violation de FK.
    # Rejoué à chaque démarrage (drop puis recreate) : idempotent par construction.
    "ALTER TABLE trade_session_items DROP CONSTRAINT IF EXISTS trade_session_items_user_card_id_fkey",
    "ALTER TABLE trade_session_items ADD CONSTRAINT trade_session_items_user_card_id_fkey "
    "FOREIGN KEY (user_card_id) REFERENCES user_cards(id) ON DELETE SET NULL",
    # Messagerie : politique de réception des cadeaux (même forme que
    # trade_request_policy), + colonnes de la table messages.
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS gift_policy VARCHAR(20) NOT NULL DEFAULT 'friends'",
    "ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_reward_card_id_fkey",
    "ALTER TABLE messages ADD CONSTRAINT messages_reward_card_id_fkey "
    "FOREIGN KEY (reward_card_id) REFERENCES user_cards(id) ON DELETE SET NULL",
    # Progression : niveaux (paliers de puissance) et achievements.
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS cards_recycled INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS claimed_level INTEGER NOT NULL DEFAULT 0",
    # Un palier de niveau peut AUSSI donner un booster (crédité à l'inventaire,
    # cf. app/models/booster_inventory.py), en plus d'une récompense en ressource.
    "ALTER TABLE level_tiers ADD COLUMN IF NOT EXISTS reward_booster_id VARCHAR(30)",
    # Correctif : "first_pack" avait le même metric ("total_cards") que la
    # chaîne cards_10/50/100/250/500, ce qui les fusionnait par erreur dans le
    # même "empilage" (cf. app/services/achievements.py::list_achievements) —
    # bloquait la chaîne sur first_pack tant qu'il restait non récupéré.
    "UPDATE achievement_defs SET metric = 'packs_opened' WHERE id = 'first_pack' AND metric = 'total_cards'",
    # Cadeau entre joueurs : un ou plusieurs boosters non ouverts (en plus
    # des cartes/ressources déjà possibles), cf. app/models/message.py.
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS reward_booster_id VARCHAR(30)",
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS reward_booster_qty INTEGER",
    # Une quête peut AUSSI donner un booster (même mécanique que les paliers
    # de niveau ci-dessus) — l'admin ne pouvait en configurer que pour les
    # achievements jusqu'ici (colonne manquante pour les niveaux/quêtes).
    "ALTER TABLE quest_defs ADD COLUMN IF NOT EXISTS reward_booster_id VARCHAR(30)",
    # Solde de départ par ressource à la création d'un compte — remplace le
    # 500 pièces codé en dur dans auth_service.py, éditable depuis l'admin.
    "ALTER TABLE resources ADD COLUMN IF NOT EXISTS starting_amount INTEGER NOT NULL DEFAULT 0",
    # Reroll : la puissance peut être retirée seule (ou en plus d'un autre axe).
    "ALTER TABLE shop_offers ADD COLUMN IF NOT EXISTS reroll_power BOOLEAN NOT NULL DEFAULT FALSE",
    # Vitrine enrichie : meilleure série de connexion, meilleur rang global,
    # 3 achievements affichés. La meilleure série part au moins de la série actuelle.
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS best_login_streak INTEGER NOT NULL DEFAULT 0",
    "UPDATE users SET best_login_streak = login_streak WHERE best_login_streak < login_streak",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS best_global_rank INTEGER",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS showcase_achievement_1_id VARCHAR(50)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS showcase_achievement_2_id VARCHAR(50)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS showcase_achievement_3_id VARCHAR(50)",
    # E-mail, newsletter, cosmétiques équipés.
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(254)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS newsletter_opt_in BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS equipped_avatar_frame_id VARCHAR(40)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS equipped_showcase_background_id VARCHAR(40)",
    # Boutique premium (fermée par défaut) et monnaie non échangeable.
    "ALTER TABLE game_config ADD COLUMN IF NOT EXISTS premium_shop_enabled BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE game_config ADD COLUMN IF NOT EXISTS premium_testers VARCHAR NOT NULL DEFAULT ''",
    "ALTER TABLE game_config ADD COLUMN IF NOT EXISTS game_closed BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE higher_lower_games ADD COLUMN IF NOT EXISTS total_multiplier DOUBLE PRECISION NOT NULL DEFAULT 1.0",
    "ALTER TABLE user_cards ADD COLUMN IF NOT EXISTS locked BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS max_level INTEGER NOT NULL DEFAULT 1",
    "ALTER TABLE friend_groups ADD COLUMN IF NOT EXISTS position INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE user_bonus_boosters ADD COLUMN IF NOT EXISTS min_quality_id VARCHAR(20)",
    "ALTER TABLE user_bonus_boosters ADD COLUMN IF NOT EXISTS min_jewelry_id VARCHAR(20)",
    "ALTER TABLE user_bonus_boosters ADD COLUMN IF NOT EXISTS specialty_weight_multiplier DOUBLE PRECISION",
    "ALTER TABLE user_bonus_boosters ADD COLUMN IF NOT EXISTS quality_weight_multiplier DOUBLE PRECISION",
    "ALTER TABLE user_bonus_boosters ADD COLUMN IF NOT EXISTS jewelry_weight_multiplier DOUBLE PRECISION",
    "ALTER TABLE user_bonus_boosters ADD COLUMN IF NOT EXISTS power_rolls INTEGER",
    "ALTER TABLE user_reroll_tokens ADD COLUMN IF NOT EXISTS reroll_boost DOUBLE PRECISION",
    "ALTER TABLE user_activities ADD COLUMN IF NOT EXISTS machine_failures JSON",
    "ALTER TABLE user_activities ADD COLUMN IF NOT EXISTS converter_day DATE",
    "ALTER TABLE user_activities ADD COLUMN IF NOT EXISTS converter_uses INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE game_config ADD COLUMN IF NOT EXISTS closed_message VARCHAR NOT NULL DEFAULT ''",
    "ALTER TABLE resources ADD COLUMN IF NOT EXISTS tradeable BOOLEAN NOT NULL DEFAULT TRUE",
    "ALTER TABLE shop_offers ADD COLUMN IF NOT EXISTS cosmetic_id VARCHAR(40)",
    # Cadeaux : boosters à bonus (bonus conservé) et rerolls de l'inventaire.
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS reward_booster_bonus JSON",
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS reward_reroll JSON",
    "ALTER TABLE messages ADD COLUMN IF NOT EXISTS reward_items JSON",
    # Échanges : boosters non ouverts et rerolls proposables.
    "ALTER TABLE trade_session_items ADD COLUMN IF NOT EXISTS booster_id VARCHAR(30)",
    "ALTER TABLE trade_session_items ADD COLUMN IF NOT EXISTS bonus_id INTEGER",
    "ALTER TABLE trade_session_items ADD COLUMN IF NOT EXISTS reroll_token_id INTEGER",
    # Limites d'achat réglables (jour / semaine / mois / une fois par compte)
    # et offres « lot » (plusieurs contenus).
    "ALTER TABLE shop_offers ADD COLUMN IF NOT EXISTS grants JSON NOT NULL DEFAULT '[]'::json",
    "ALTER TABLE shop_offers ADD COLUMN IF NOT EXISTS limit_period VARCHAR(10) NOT NULL DEFAULT 'none'",
    "ALTER TABLE shop_offers ADD COLUMN IF NOT EXISTS limit_count INTEGER NOT NULL DEFAULT 1",
    "UPDATE shop_offers SET limit_period = 'day', limit_count = purchase_limit_per_day "
    "WHERE purchase_limit_per_day IS NOT NULL AND limit_period = 'none'",
    "ALTER TABLE premium_products ADD COLUMN IF NOT EXISTS limit_period VARCHAR(10) NOT NULL DEFAULT 'none'",
    "ALTER TABLE premium_products ADD COLUMN IF NOT EXISTS limit_count INTEGER NOT NULL DEFAULT 1",
    "UPDATE premium_products SET limit_period = 'account', limit_count = 1 "
    "WHERE once_per_account = TRUE AND limit_period = 'none'",
    # Activités : réglages éditables depuis l'admin.
    "ALTER TABLE game_config ADD COLUMN IF NOT EXISTS activities JSON",
    # Guildes : délai après un départ.
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS guild_left_at TIMESTAMP",
    # Carte précise du shop : puissance tirée à l'achat ou fixée par l'admin.
    "ALTER TABLE shop_offers ADD COLUMN IF NOT EXISTS card_power_mode VARCHAR(10) NOT NULL DEFAULT 'rolled'",
    "ALTER TABLE shop_offers ADD COLUMN IF NOT EXISTS card_power INTEGER",
    # Compteurs pour les nouvelles statistiques / achievements / quêtes.
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS dust_from_recycling INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS rerolls_used INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS reroll_rarity_upgrades INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS best_reroll_card_id VARCHAR(40)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS best_reroll_combined_rarity BIGINT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS login_days_total INTEGER NOT NULL DEFAULT 0",
    # Distinctions : tag de survie à une remise à zéro (vrai par défaut —
    # oublier le tag ne doit jamais faire disparaître « Fondateur »).
    "ALTER TABLE distinctions ADD COLUMN IF NOT EXISTS keeps_on_reset BOOLEAN NOT NULL DEFAULT TRUE",
    # Borne des limites « une fois par compte » : les achats d'avant la
    # dernière remise à zéro ne bloquent plus les offres à usage unique.
    "ALTER TABLE game_config ADD COLUMN IF NOT EXISTS last_reset_at TIMESTAMP",
    # Plage de puissance indépendante de la taille du set.
    "ALTER TABLE user_cards ADD COLUMN IF NOT EXISTS power_probability DOUBLE PRECISION NOT NULL DEFAULT 0",
    # Jours de connexion déjà cumulés avant le compteur : au moins la meilleure série.
    "UPDATE users SET login_days_total = best_login_streak WHERE login_days_total < best_login_streak",
    # Achievements de série : basés sur la meilleure série atteinte (plus perdus si la série casse).
    "UPDATE achievement_defs SET metric = 'best_login_streak' "
    "WHERE id IN ('streak_7', 'streak_30', 'streak_100') AND metric = 'login_streak'",
]

# Boosters offerts à certains paliers de niveau (en plus des pièces) —
# appliqué après le seed des paliers eux-mêmes (cf. plus bas dans apply_patches).
_LEVEL_BOOSTER_REWARDS = {10: "booster_A1", 20: "booster_A1"}

# Types de personnage initiaux (portés depuis l'ancien TYPE_COLORS du renderer).
_DEFAULT_TYPES = [
    ("plantes", "Plantes", 60, 180, 75),
    ("feu", "Feu", 220, 60, 40),
    ("eau", "Eau", 50, 120, 220),
    ("electrique", "Électrique", 255, 210, 50),
    ("tenebres", "Ténèbres", 80, 50, 120),
    ("lumiere", "Lumière", 255, 240, 180),
    ("glace", "Glace", 150, 220, 255),
    ("roche", "Roche", 160, 130, 90),
    ("vent", "Vent", 170, 220, 200),
    ("poison", "Poison", 170, 80, 200),
    ("metal", "Métal", 160, 170, 185),
    ("psychique", "Psychique", 230, 100, 180),
    ("dragon", "Dragon", 100, 60, 200),
    ("fee", "Fée", 255, 150, 200),
    ("combat", "Combat", 180, 50, 30),
    ("normal", "Normal", 150, 150, 150),
]

# Ressources par défaut (recyclage / shop). "coins" est la ressource système
# (pièces) : non supprimable, existe de base pour chaque joueur via User.coins
# plutôt qu'une ligne UserResource (cf. services/wallet.py).
_DEFAULT_RESOURCES = [
    ("coins", "Pièces", "Monnaie de base. Ne peut pas être supprimée."),
    ("dust", "Poussière", "Obtenue en recyclant des cartes. Dépensable au shop."),
    ("shards", "Éclats", "Monnaie premium, achetée en euros. Liée au compte : ni échangeable ni offrable."),
    *NEW_RESOURCES,
]
_PROTECTED_RESOURCES = {"coins", "shards"}
_NON_TRADEABLE_RESOURCES = {"shards"}

# Paliers de niveau par défaut (level, power_required, reward_amount en
# pièces). Calé sur la refonte de l'équilibrage : une carte apporte au plus
# LEVEL_CONTRIBUTION_CAP au niveau, ce qui donne ~290 de progression par
# booster. Le niveau 10 demande donc environ 90 boosters — deux journées en
# jouant bien, trois en jouant mollement — et le niveau 20 reste à des
# semaines. À retoucher depuis l'admin si l'économie bouge.
_DEFAULT_LEVEL_TIERS = [
    (1, 0, None), (2, 900, 100), (3, 2_000, 150), (4, 3_700, 200),
    (5, 6_000, 300), (6, 8_800, 400), (7, 12_300, 500), (8, 16_200, 650),
    (9, 20_500, 800), (10, 25_000, 1_000), (11, 30_000, 1_200), (12, 35_900, 1_500),
    (13, 42_000, 1_800), (14, 49_000, 2_200), (15, 56_700, 2_700), (16, 64_500, 3_300),
    (17, 73_500, 4_000), (18, 84_000, 4_800), (19, 95_500, 5_800), (20, 110_000, 7_000),
]

# Ancien barème, d'avant la division des plafonds de puissance. Une base
# existante garde ses lignes : on ne les remet à jour que si elles portent
# encore EXACTEMENT l'ancienne valeur — un palier retouché en admin reste
# intact (même précaution que pour les autres valeurs seedées).
_PREVIOUS_LEVEL_TIERS = {
    2: 1_000, 3: 2_500, 4: 5_000, 5: 8_500, 6: 13_000, 7: 19_000, 8: 27_000,
    9: 37_000, 10: 50_000, 11: 65_000, 12: 85_000, 13: 110_000, 14: 140_000,
    15: 175_000, 16: 220_000, 17: 275_000, 18: 340_000, 19: 420_000, 20: 520_000,
}

# id, name, description, category, metric, threshold, metric_param,
# reward_resource_id, reward_amount, reward_booster_id
_DEFAULT_ACHIEVEMENTS = [
    ("first_pack", "Premier pas", "Ouvrir ton tout premier booster.", "collection", "packs_opened", 1, None, "coins", 50, None),
    ("cards_10", "Petite collection", "Posséder 10 cartes.", "collection", "total_cards", 10, None, "coins", 100, None),
    ("cards_50", "Collectionneur", "Posséder 50 cartes.", "collection", "total_cards", 50, None, "coins", 250, None),
    ("cards_100", "Grand collectionneur", "Posséder 100 cartes.", "collection", "total_cards", 100, None, "coins", 500, None),
    ("cards_250", "Collection imposante", "Posséder 250 cartes.", "collection", "total_cards", 250, None, "coins", 1_000, None),
    ("cards_500", "Collection légendaire", "Posséder 500 cartes.", "collection", "total_cards", 500, None, "coins", 2_000, None),
    ("first_rare", "Un peu de chance", "Obtenir ta première carte Rare.", "collection", "rarity_owned", 1, "rare", "dust", 100, None),
    ("first_epic", "Belle prise", "Obtenir ta première carte Epic.", "collection", "rarity_owned", 1, "epic", "dust", 250, None),
    ("first_legendary", "Jackpot", "Obtenir ta première carte Legendary.", "collection", "rarity_owned", 1, "legendary", "dust", 500, None),
    ("first_jewelry_silver", "Éclat d'argent", "Obtenir ta première carte avec un bijou argent.", "collection", "jewelry_owned", 1, "silver", "dust", 100, None),
    ("first_jewelry_gold", "Éclat d'or", "Obtenir ta première carte avec un bijou or.", "collection", "jewelry_owned", 1, "gold", "dust", 200, None),
    ("first_jewelry_diamond", "Éclat de diamant", "Obtenir ta première carte avec un bijou diamant.", "collection", "jewelry_owned", 1, "diamond", "dust", 400, None),
    ("first_jewelry_prismatic", "Éclat prismatique", "Obtenir ta première carte avec un bijou prismatique.", "collection", "jewelry_owned", 1, "prismatic", "dust", 800, None),
    ("first_shiny", "Ça brille", "Obtenir ta première carte Shiny.", "collection", "specialty_owned", 1, "shiny", "dust", 300, None),
    ("first_full_art", "Toile complète", "Obtenir ta première carte Full Art.", "collection", "specialty_owned", 1, "full_art", "dust", 200, None),
    ("first_ex", "Format EX", "Obtenir ta première carte EX.", "collection", "specialty_owned", 1, "ex", "dust", 250, None),
    ("one_of_each_type", "Touche-à-tout", "Posséder au moins une carte de chaque type existant.", "collection", "types_owned_distinct", 9_999, None, "coins", 500, None),
    ("type_master", "Spécialiste", "Posséder toutes les cartes d'un même type.", "collection", "type_complete", 1, None, None, None, "booster_A1"),
    ("power_1000", "Montée en puissance", "Obtenir une carte de puissance ≥ 1000.", "collection", "card_power", 1_000, None, "coins", 200, None),
    ("power_5000", "Puissance rare", "Obtenir une carte de puissance ≥ 5000.", "collection", "card_power", 5_000, None, "coins", 500, None),
    ("power_10000", "Puissance maximale", "Obtenir une carte de puissance ≥ 10000.", "collection", "card_power", 10_000, None, "coins", 1_000, None),
    ("lucky_rare", "Coup du destin", "Obtenir une carte de rareté globale 1 sur 10 000 ou plus.", "collection", "combined_rarity", 10_000, None, "dust", 500, None),
    ("first_friend", "Pas si seul", "Ajouter ton premier ami.", "social", "friends_count", 1, None, "coins", 50, None),
    ("friends_10", "Populaire", "Avoir 10 amis.", "social", "friends_count", 10, None, "coins", 300, None),
    ("friends_25", "Grand réseau", "Avoir 25 amis.", "social", "friends_count", 25, None, "coins", 600, None),
    ("first_trade", "Premier échange", "Conclure ton premier échange.", "social", "trades_completed", 1, None, "coins", 100, None),
    ("trades_10", "Marchand", "Conclure 10 échanges.", "social", "trades_completed", 10, None, "coins", 300, None),
    ("trades_100", "Grand marchand", "Conclure 100 échanges.", "social", "trades_completed", 100, None, "coins", 1_500, None),
    ("first_gift", "Générosité", "Envoyer ton premier cadeau.", "social", "gifts_sent", 1, None, "dust", 50, None),
    ("gifts_10", "Père Noël", "Envoyer 10 cadeaux.", "social", "gifts_sent", 10, None, "dust", 200, None),
    ("gifts_50", "Philanthrope", "Envoyer 50 cadeaux.", "social", "gifts_sent", 50, None, "dust", 600, None),
    ("recycle_10", "Recycleur", "Recycler 10 cartes.", "economy", "cards_recycled", 10, None, "coins", 100, None),
    ("recycle_100", "Grand recycleur", "Recycler 100 cartes.", "economy", "cards_recycled", 100, None, "coins", 500, None),
    ("rich_10k", "À l'aise", "Avoir 10 000 pièces en banque en même temps.", "economy", "coins_balance", 10_000, None, "dust", 200, None),
    ("rich_100k", "Fortune", "Avoir 100 000 pièces en banque en même temps.", "economy", "coins_balance", 100_000, None, "dust", 1_000, None),
    ("level_5", "Niveau 5", "Atteindre le niveau 5.", "progression", "level", 5, None, "coins", 200, None),
    ("level_10", "Niveau 10", "Atteindre le niveau 10.", "progression", "level", 10, None, "coins", 500, None),
    ("level_20", "Niveau 20", "Atteindre le niveau 20.", "progression", "level", 20, None, "coins", 1_200, None),
    ("streak_7", "Une semaine", "Une série de connexion de 7 jours.", "progression", "login_streak", 7, None, "coins", 150, None),
    ("streak_30", "Un mois", "Une série de connexion de 30 jours.", "progression", "login_streak", 30, None, "coins", 500, None),
    ("streak_100", "Fidèle", "Une série de connexion de 100 jours.", "progression", "login_streak", 100, None, "coins", 2_000, None),
    ("shop_1", "Premier achat", "Faire ton premier achat en boutique.", "economy", "shop_purchases", 1, None, "coins", 50, None),
    ("shop_10", "Client fidèle", "Faire 10 achats en boutique.", "economy", "shop_purchases", 10, None, "coins", 200, None),
    ("shop_50", "Accro du shopping", "Faire 50 achats en boutique.", "economy", "shop_purchases", 50, None, "coins", 600, None),
    ("shop_200", "Grand client", "Faire 200 achats en boutique.", "economy", "shop_purchases", 200, None, "dust", 1_500, None),
    ("reroll_1", "Deuxième chance", "Utiliser ton premier reroll.", "economy", "rerolls_used", 1, None, "coins", 50, None),
    ("reroll_10", "Tenace", "Utiliser 10 rerolls.", "economy", "rerolls_used", 10, None, "coins", 250, None),
    ("reroll_50", "Perfectionniste", "Utiliser 50 rerolls.", "economy", "rerolls_used", 50, None, "dust", 600, None),
    ("reroll_upgrade_1", "Coup de pouce", "Obtenir une meilleure rareté grâce à un reroll.", "economy", "reroll_rarity_upgrades", 1, None, "dust", 150, None),
    ("reroll_upgrade_10", "Alchimiste", "Améliorer 10 fois la rareté d'une carte par reroll.", "economy", "reroll_rarity_upgrades", 10, None, "dust", 800, None),
    ("quests_1", "Première mission", "Terminer ta première quête.", "progression", "quests_completed", 1, None, "coins", 50, None),
    ("quests_10", "Aventurier", "Terminer 10 quêtes.", "progression", "quests_completed", 10, None, "coins", 250, None),
    ("quests_50", "Vétéran des quêtes", "Terminer 50 quêtes.", "progression", "quests_completed", 50, None, "coins", 800, None),
    ("quests_200", "Légende des quêtes", "Terminer 200 quêtes.", "progression", "quests_completed", 200, None, None, None, "booster_A1"),
    ("rank_top10", "Dans le top 10", "Atteindre le top 10 du classement global.", "progression", "rank_reached", 1, "10", "coins", 300, None),
    ("rank_top3", "Sur le podium", "Atteindre le top 3 du classement global.", "progression", "rank_reached", 1, "3", "coins", 800, None),
    ("rank_1", "Numéro un", "Atteindre la 1re place du classement global.", "progression", "rank_reached", 1, "1", "dust", 2_000, None),
    ("completion_25", "Quart de collection", "Posséder 25 % des personnages.", "collection", "collection_completion_pct", 25, None, "coins", 200, None),
    ("completion_50", "Mi-collection", "Posséder 50 % des personnages.", "collection", "collection_completion_pct", 50, None, "coins", 500, None),
    ("completion_75", "Presque complet", "Posséder 75 % des personnages.", "collection", "collection_completion_pct", 75, None, "coins", 1_000, None),
    ("completion_100", "Collection complète", "Posséder tous les personnages.", "collection", "collection_completion_pct", 100, None, None, None, "booster_A1"),
    ("legendary_5", "Trésor légendaire", "Posséder 5 cartes légendaires.", "collection", "rarity_count", 5, "legendary", "dust", 500, None),
    ("legendary_25", "Panthéon", "Posséder 25 cartes légendaires.", "collection", "rarity_count", 25, "legendary", "dust", 2_000, None),
    ("shiny_prismatic", "Éclat absolu", "Posséder une carte Shiny avec un bijou prismatique.", "collection", "specialty_jewelry_owned", 1, "shiny:prismatic", "dust", 1_000, None),
    ("halfway_there", "À mi-chemin", "Débloquer la moitié des autres achievements.", "meta", "meta_unlocked_ratio", 50, None, "coins", 1_000, None),
]

# id, name, description, period, metric, threshold, reward_resource_id, reward_amount
_DEFAULT_QUESTS = [
    ("d_open_1_pack", "Petit tirage", "Ouvre 1 booster.", "daily", "packs_opened", 1, "coins", 30),
    ("d_open_3_packs", "Ouverture groupée", "Ouvre 3 boosters.", "daily", "packs_opened", 3, "coins", 80),
    ("d_recycle_1", "Tri du jour", "Recycle 1 carte.", "daily", "cards_recycled", 1, "dust", 20),
    ("d_recycle_3", "Grand tri", "Recycle 3 cartes.", "daily", "cards_recycled", 3, "dust", 50),
    ("d_trade_1", "Petit échange", "Conclue un échange.", "daily", "trades_completed", 1, "coins", 50),
    ("d_gift_1", "Petit geste", "Envoie un cadeau.", "daily", "gifts_sent", 1, "coins", 40),
    ("d_friend_request_1", "Nouvelle rencontre", "Envoie une demande d'ami.", "daily", "friend_requests_sent", 1, "coins", 30),
    ("w_open_10_packs", "Semaine chargée", "Ouvre 10 boosters cette semaine.", "weekly", "packs_opened", 10, "coins", 300),
    ("w_trade_3", "Négociateur", "Conclue 3 échanges cette semaine.", "weekly", "trades_completed", 3, "coins", 250),
    ("w_recycle_10", "Grand ménage", "Recycle 10 cartes cette semaine.", "weekly", "cards_recycled", 10, "dust", 150),
    ("w_gift_5", "Cœur généreux", "Envoie 5 cadeaux cette semaine.", "weekly", "gifts_sent", 5, "coins", 200),
    ("d_shop_3", "Emplettes", "Fais 3 achats en boutique.", "daily", "shop_purchases", 3, "coins", 40),
    ("d_reroll_1", "Retente ta chance", "Utilise 1 reroll.", "daily", "rerolls_used", 1, "dust", 30),
    ("d_rare_3", "Chasseur de rares", "Obtiens 3 cartes rares ou mieux (booster ou reroll).", "daily", "rare_cards_obtained", 3, "coins", 60),
    ("w_shop_15", "Habitué de la boutique", "Fais 15 achats en boutique cette semaine.", "weekly", "shop_purchases", 15, "coins", 250),
    ("w_reroll_5", "Bricoleur", "Utilise 5 rerolls cette semaine.", "weekly", "rerolls_used", 5, "dust", 150),
    ("w_legendary_1", "Chasse au trésor", "Obtiens 1 carte légendaire cette semaine (booster ou reroll).", "weekly", "legendary_cards_obtained", 1, "coins", 400),
    ("w_daily_5", "Assidu", "Récupère la récompense du jour 5 fois cette semaine.", "weekly", "daily_rewards_claimed", 5, "coins", 300),
    ("w_friend_request_3", "Réseau grandissant", "Envoie 3 demandes d'ami cette semaine.", "weekly", "friend_requests_sent", 3, "coins", 150),
]

# Paliers d'Éclats vendus en euros (argent réel -> Éclats uniquement) :
# id, nom, prix en centimes, Éclats crédités. Modifiables depuis l'admin.
_DEFAULT_SHARD_PACKS = [
    ("shards_099", "Poignée d'Éclats", 99, 90),
    ("shards_499", "Petit sac d'Éclats", 499, 550),
    ("shards_999", "Sac d'Éclats", 999, 1_150),
    ("shards_1999", "Grand sac d'Éclats", 1_999, 2_400),
    ("shards_4999", "Coffre d'Éclats", 4_999, 6_250),
    ("shards_9999", "Trésor d'Éclats", 9_999, 13_000),
]

async def apply_patches(conn: AsyncConnection) -> None:
    for sql in _STATEMENTS:
        try:
            await conn.execute(text(sql))
        except Exception as exc:  # noqa: BLE001 - patch best-effort, ne bloque pas le démarrage
            logger.warning("sur %r...: %s", sql[:60], exc)

    insert_type = text(
        "INSERT INTO character_types (id, name, color_r, color_g, color_b) "
        "VALUES (:id, :name, :r, :g, :b) ON CONFLICT (id) DO NOTHING"
    )
    for type_id, name, r, g, b in _DEFAULT_TYPES:
        try:
            await conn.execute(insert_type, {"id": type_id, "name": name, "r": r, "g": g, "b": b})
        except Exception as exc:  # noqa: BLE001
            logger.warning("seed type %r: %s", type_id, exc)

    insert_resource = text(
        # Toutes les colonnes explicitement : sur une base neuve (create_all), les
        # valeurs par défaut du modèle ne sont pas des DEFAULT SQL.
        "INSERT INTO resources (id, name, description, protected, starting_amount, tradeable) "
        "VALUES (:id, :name, :description, :protected, 0, :tradeable) ON CONFLICT (id) DO NOTHING"
    )
    for res_id, name, description in _DEFAULT_RESOURCES:
        try:
            await conn.execute(insert_resource, {
                "id": res_id, "name": name, "description": description,
                "protected": res_id in _PROTECTED_RESOURCES,
                "tradeable": res_id not in _NON_TRADEABLE_RESOURCES,
            })
        except Exception as exc:  # noqa: BLE001
            logger.warning("seed resource %r: %s", res_id, exc)

    # Au cas où "coins" existait déjà avant l'ajout de la colonne `protected`
    # (déploiement antérieur) : force le flag, ne dépend pas de l'ordre d'insertion.
    force_protected = text("UPDATE resources SET protected = TRUE WHERE id = :id")
    for res_id in _PROTECTED_RESOURCES:
        try:
            await conn.execute(force_protected, {"id": res_id})
        except Exception as exc:  # noqa: BLE001
            logger.warning("protected %r: %s", res_id, exc)

    for res_id in _NON_TRADEABLE_RESOURCES:
        try:
            await conn.execute(text("UPDATE resources SET tradeable = FALSE WHERE id = :id"), {"id": res_id})
        except Exception as exc:  # noqa: BLE001
            logger.warning("non tradeable %r: %s", res_id, exc)

    # Solde de départ historique des pièces (500) — ne stomp pas un réglage
    # déjà fait par un admin, même logique que les autres colonnes seedées.
    try:
        await conn.execute(text(
            "UPDATE resources SET starting_amount = 500 WHERE id = 'coins' AND starting_amount = 0"
        ))
    except Exception as exc:  # noqa: BLE001
        logger.warning("starting_amount coins: %s", exc)

    insert_tier = text(
        "INSERT INTO level_tiers (level, power_required, reward_resource_id, reward_amount) "
        "VALUES (:level, :power_required, :reward_resource_id, :reward_amount) ON CONFLICT (level) DO NOTHING"
    )
    for level, power_required, reward_amount in _DEFAULT_LEVEL_TIERS:
        try:
            await conn.execute(insert_tier, {
                "level": level, "power_required": power_required,
                "reward_resource_id": "coins" if reward_amount else None, "reward_amount": reward_amount,
            })
        except Exception as exc:  # noqa: BLE001
            logger.warning("seed level tier %r: %s", level, exc)

    rebalance_tier = text(
        "UPDATE level_tiers SET power_required = :new WHERE level = :level AND power_required = :old"
    )
    for level, power_required, _ in _DEFAULT_LEVEL_TIERS:
        ancienne = _PREVIOUS_LEVEL_TIERS.get(level)
        if ancienne is None or ancienne == power_required:
            continue
        try:
            await conn.execute(rebalance_tier, {"level": level, "new": power_required, "old": ancienne})
        except Exception as exc:  # noqa: BLE001
            logger.warning("rebalance level tier %r: %s", level, exc)

    # Ne renseigne le booster-bonus que si la colonne est encore vide (ne
    # stomp pas un réglage déjà fait par un admin).
    set_level_booster = text(
        "UPDATE level_tiers SET reward_booster_id = :booster_id "
        "WHERE level = :level AND reward_booster_id IS NULL"
    )
    for level, booster_id in _LEVEL_BOOSTER_REWARDS.items():
        try:
            await conn.execute(set_level_booster, {"level": level, "booster_id": booster_id})
        except Exception as exc:  # noqa: BLE001
            logger.warning("level booster reward %r: %s", level, exc)

    insert_achievement = text(
        "INSERT INTO achievement_defs "
        "(id, name, description, category, metric, threshold, metric_param, "
        " reward_resource_id, reward_amount, reward_booster_id, active) "
        "VALUES (:id, :name, :description, :category, :metric, :threshold, :metric_param, "
        " :reward_resource_id, :reward_amount, :reward_booster_id, TRUE) ON CONFLICT (id) DO NOTHING"
    )
    for (a_id, name, description, category, metric, threshold, metric_param,
         reward_resource_id, reward_amount, reward_booster_id) in _DEFAULT_ACHIEVEMENTS:
        try:
            await conn.execute(insert_achievement, {
                "id": a_id, "name": name, "description": description, "category": category,
                "metric": metric, "threshold": threshold, "metric_param": metric_param,
                "reward_resource_id": reward_resource_id, "reward_amount": reward_amount,
                "reward_booster_id": reward_booster_id,
            })
        except Exception as exc:  # noqa: BLE001
            logger.warning("seed achievement %r: %s", a_id, exc)

    insert_quest = text(
        "INSERT INTO quest_defs (id, name, description, period, metric, threshold, "
        " reward_resource_id, reward_amount, active) "
        "VALUES (:id, :name, :description, :period, :metric, :threshold, "
        " :reward_resource_id, :reward_amount, TRUE) ON CONFLICT (id) DO NOTHING"
    )
    for (q_id, name, description, period, metric, threshold,
         reward_resource_id, reward_amount) in _DEFAULT_QUESTS:
        try:
            await conn.execute(insert_quest, {
                "id": q_id, "name": name, "description": description, "period": period,
                "metric": metric, "threshold": threshold,
                "reward_resource_id": reward_resource_id, "reward_amount": reward_amount,
            })
        except Exception as exc:  # noqa: BLE001
            logger.warning("seed quest %r: %s", q_id, exc)

    insert_pack = text(
        "INSERT INTO premium_products (id, name, description, price_cents, currency, grants, "
        " once_per_account, limit_period, limit_count, active, sort_order) "
        "VALUES (:id, :name, '', :price_cents, 'eur', CAST(:grants AS JSON), FALSE, 'none', 1, TRUE, :sort_order) "
        "ON CONFLICT (id) DO NOTHING"
    )
    for order, (pack_id, name, price_cents, shards) in enumerate(_DEFAULT_SHARD_PACKS):
        try:
            await conn.execute(insert_pack, {
                "id": pack_id, "name": name, "price_cents": price_cents,
                "grants": json.dumps([{"kind": "resource", "id": "shards", "amount": shards}]),
                "sort_order": order,
            })
        except Exception as exc:  # noqa: BLE001
            logger.warning("seed shard pack %r: %s", pack_id, exc)

    # Réglages globaux (récompense quotidienne) — ligne singleton, remplace
    # les anciennes variables d'environnement DAILY_BASE_REWARD/DAILY_STREAK_BONUS.
    try:
        await conn.execute(text(
            "INSERT INTO game_config (id, daily_base_reward, daily_streak_bonus, premium_shop_enabled, premium_testers) "
            "VALUES (1, 500, 100, FALSE, '') ON CONFLICT (id) DO NOTHING"
        ))
    except Exception as exc:  # noqa: BLE001
        logger.warning("seed game_config: %s", exc)

    await _add_resource_converter_pairs(conn)
    await _replay_rebalance_settings(conn)

    # Backfill de la puissance (colonne ajoutée après coup) pour les cartes
    # déjà en base — chacune reçoit un tirage rétroactif, une seule fois.
    try:
        rows = (await conn.execute(text(
            "SELECT id, drop_probability, rarity_id, quality_id, specialty_id, jewelry_id "
            "FROM user_cards WHERE power IS NULL AND drop_probability > 0"
        ))).all()
        if rows:
            update_power = text("UPDATE user_cards SET power = :power WHERE id = :id")
            for row in rows:
                power = roll_power(
                    row.drop_probability, row.rarity_id, row.quality_id,
                    row.specialty_id, row.jewelry_id,
                )
                if power is not None:
                    await conn.execute(update_power, {"id": row.id, "power": power})
            logger.info("Puissance calculée pour %d carte(s) existante(s).", len(rows))
    except Exception as exc:  # noqa: BLE001
        logger.warning("backfill power: %s", exc)

    # Probabilité de BASE de chaque carte (son set, poids normaux) et puissance
    # plafonnée au maximum qui en découle : les cartes tirées avec de la chance
    # (présence, guilde, garantie, booster multi-sets) pouvaient dépasser le
    # maximum affiché. Idempotent : ne réécrit que les cartes qui changent.
    try:
        await _normalize_card_powers(conn)
    except Exception as exc:  # noqa: BLE001
        logger.warning("normalisation des puissances : %s", exc)


async def _add_resource_converter_pairs(conn: AsyncConnection) -> None:
    """Paires du convertisseur des ressources de recyclage, ajoutées une seule fois
    aux réglages déjà enregistrés depuis l'admin : une liste enregistrée remplace
    celle par défaut (cf. activities_config._merge), les nouvelles n'apparaîtraient pas."""
    marker = "recycling_resources_v1"
    try:
        row = (await conn.execute(text("SELECT activities FROM game_config WHERE id = 1"))).first()
        stored = row[0] if row else None
        if isinstance(stored, str):
            stored = json.loads(stored)
        if not stored or marker in stored.get("_applied", []):
            return
        pairs = (stored.get("converter") or {}).get("pairs")
        if pairs is not None:
            known = {(p.get("from"), p.get("to")) for p in pairs}
            pairs.extend(p for p in converter_pairs() if (p["from"], p["to"]) not in known)
        stored["_applied"] = [*stored.get("_applied", []), marker]
        await conn.execute(
            text("UPDATE game_config SET activities = CAST(:v AS JSON) WHERE id = 1"), {"v": json.dumps(stored)},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("paires du convertisseur : %s", exc)


# Réglages que la refonte de l'équilibrage a changés dans le code, et qu'une
# base existante ne reprendrait jamais : `save_config` y fige une copie
# COMPLÈTE des réglages, si bien qu'une nouvelle valeur par défaut n'atteint
# pas le jeu. Rejoués une seule fois (marqueur), pour qu'un réglage refait
# ensuite depuis l'admin reste maître.
_REBALANCE_SETTINGS = (
    "presence", "progression.presence_max", "unlocks.higher_lower", "unlocks.showcase",
)


async def _replay_rebalance_settings(conn: AsyncConnection) -> None:
    marker = "rebalance_power_v2"
    try:
        row = (await conn.execute(text("SELECT activities FROM game_config WHERE id = 1"))).first()
        stored = row[0] if row else None
        if isinstance(stored, str):
            stored = json.loads(stored)
        if not stored or marker in stored.get("_applied", []):
            return
        for chemin in _REBALANCE_SETTINGS:
            parties = chemin.split(".")
            source, cible = ACTIVITIES_DEFAULTS, stored
            for partie in parties[:-1]:
                source = source[partie]
                cible = cible.setdefault(partie, {})
            cible[parties[-1]] = copy.deepcopy(source[parties[-1]])
        stored["_applied"] = [*stored.get("_applied", []), marker]
        await conn.execute(
            text("UPDATE game_config SET activities = CAST(:v AS JSON) WHERE id = 1"), {"v": json.dumps(stored)},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("rejeu des réglages d'équilibrage : %s", exc)


async def _normalize_card_powers(conn: AsyncConnection) -> None:
    def weights(table: str) -> dict[str, float]:
        return {r.id: r.weight for r in rows[table]}

    rows = {}
    for table in ("rarities", "qualities", "specialties", "jewelries"):
        rows[table] = (await conn.execute(text(f"SELECT id, weight FROM {table}"))).all()
    axis = {t: weights(t) for t in rows}
    totals = {t: sum(w.values()) for t, w in axis.items()}
    links = (await conn.execute(text("SELECT set_id, character_id, weight FROM character_sets"))).all()
    full_art_chars = {r.id for r in (await conn.execute(text("SELECT id FROM characters WHERE full_art"))).all()}
    link_weight = {(l.set_id, l.character_id): l.weight for l in links}
    set_totals: dict[str, float] = {}
    for l in links:
        set_totals[l.set_id] = set_totals.get(l.set_id, 0) + l.weight

    def frac(table: str, id_: str) -> float:
        total = totals[table]
        return (axis[table].get(id_, 0) / total) if total else 0.0

    cards = (await conn.execute(text(
        "SELECT id, character_id, set_id, rarity_id, quality_id, specialty_id, jewelry_id, "
        "drop_probability, power FROM user_cards"
    ))).all()
    update = text("UPDATE user_cards SET drop_probability = :p, power = :power WHERE id = :id")
    changed = capped = 0
    for c in cards:
        total = set_totals.get(c.set_id, 0)
        char = (link_weight.get((c.set_id, c.character_id), 0) / total) if total else 0.0
        specialty = frac("specialties", c.specialty_id)
        if c.specialty_id == "normal" and c.character_id not in full_art_chars:
            specialty += frac("specialties", "full_art")
        base = (char * frac("rarities", c.rarity_id) * frac("qualities", c.quality_id)
                * specialty * frac("jewelries", c.jewelry_id))
        if base <= 0:
            continue  # référentiel incomplet : on ne touche pas à la carte
        n = power_range(base, c.rarity_id, c.quality_id, c.specialty_id, c.jewelry_id)
        power = c.power
        if power is not None and n is not None and power > n:
            power = n
            capped += 1
        old = c.drop_probability or 0.0
        if power != c.power or abs(old - base) > base * 1e-9:
            await conn.execute(update, {"p": base, "power": power, "id": c.id})
            changed += 1
    if changed:
        logger.info("Puissances normalisées : %d carte(s) mises à jour, %d ramenée(s) au maximum.", changed, capped)
