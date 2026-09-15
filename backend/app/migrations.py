"""
Petits correctifs de schéma et de données, idempotents, appliqués au démarrage
juste après `SQLModel.metadata.create_all` (qui ne crée que les tables
manquantes — pas les colonnes ajoutées sur une table déjà existante).

Chaque étape doit pouvoir être rejouée sans risque à chaque démarrage.
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.services.power import roll_power

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
]
_PROTECTED_RESOURCES = {"coins"}

# Paliers de niveau par défaut (level, power_required, reward_amount en
# pièces) — calibré sur le roster actuel (1 personnage) : à retoucher depuis
# l'admin quand le roster grossit (la puissance moyenne par carte augmente
# avec le nombre de personnages, cf. conversation de conception).
_DEFAULT_LEVEL_TIERS = [
    (1, 0, None), (2, 1_000, 100), (3, 2_500, 150), (4, 5_000, 200),
    (5, 8_500, 300), (6, 13_000, 400), (7, 19_000, 500), (8, 27_000, 650),
    (9, 37_000, 800), (10, 50_000, 1_000), (11, 65_000, 1_200), (12, 85_000, 1_500),
    (13, 110_000, 1_800), (14, 140_000, 2_200), (15, 175_000, 2_700), (16, 220_000, 3_300),
    (17, 275_000, 4_000), (18, 340_000, 4_800), (19, 420_000, 5_800), (20, 520_000, 7_000),
]

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
    ("w_friend_request_3", "Réseau grandissant", "Envoie 3 demandes d'ami cette semaine.", "weekly", "friend_requests_sent", 3, "coins", 150),
]

# Valeurs de recyclage par défaut, par table et par id. Appliquées uniquement
# si la valeur est encore à 0 (ne stomp pas un réglage déjà fait par un admin).
_RECYCLE_DEFAULTS: dict[str, dict[str, int]] = {
    "rarities": {"common": 5, "rare": 20, "epic": 60, "legendary": 200},
    "qualities": {
        "authentic": 500, "mint": 300, "graded": 200, "excellent": 120,
        "preserved": 60, "fair": 40, "worn": 25, "faded": 15,
        "scratched": 10, "torn": 6, "damaged": 4,
        "unplayable": 2, "unreadable": 2, "destroyed": 1,
    },
    "specialties": {"normal": 0, "full_art": 50, "ex": 80, "shiny": 150},
    "jewelries": {"none": 0, "silver": 20, "gold": 60, "diamond": 150, "prismatic": 400},
}


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
        "INSERT INTO resources (id, name, description, protected) "
        "VALUES (:id, :name, :description, :protected) ON CONFLICT (id) DO NOTHING"
    )
    for res_id, name, description in _DEFAULT_RESOURCES:
        try:
            await conn.execute(insert_resource, {
                "id": res_id, "name": name, "description": description,
                "protected": res_id in _PROTECTED_RESOURCES,
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

    # Ne renseigne le booster-bonus que si la colonne est encore vide (ne
    # stomp pas un réglage déjà fait par un admin), même logique que recycle_value.
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

    for table, values in _RECYCLE_DEFAULTS.items():
        update = text(
            f"UPDATE {table} SET recycle_value = :v WHERE id = :id AND recycle_value = 0"
        )
        for row_id, value in values.items():
            try:
                await conn.execute(update, {"id": row_id, "v": value})
            except Exception as exc:  # noqa: BLE001
                logger.warning("recycle_value %s.%s: %s", table, row_id, exc)

    # Réglages globaux (récompense quotidienne) — ligne singleton, remplace
    # les anciennes variables d'environnement DAILY_BASE_REWARD/DAILY_STREAK_BONUS.
    try:
        await conn.execute(text(
            "INSERT INTO game_config (id, daily_base_reward, daily_streak_bonus) "
            "VALUES (1, 500, 100) ON CONFLICT (id) DO NOTHING"
        ))
    except Exception as exc:  # noqa: BLE001
        logger.warning("seed game_config: %s", exc)

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
