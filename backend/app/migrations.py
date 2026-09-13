"""
Petits correctifs de schéma et de données, idempotents, appliqués au démarrage
juste après `SQLModel.metadata.create_all` (qui ne crée que les tables
manquantes — pas les colonnes ajoutées sur une table déjà existante).

Chaque étape doit pouvoir être rejouée sans risque à chaque démarrage.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.services.power import roll_power

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
]

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
            print(f"[migrations] avertissement sur {sql[:60]!r}...: {exc}")

    insert_type = text(
        "INSERT INTO character_types (id, name, color_r, color_g, color_b) "
        "VALUES (:id, :name, :r, :g, :b) ON CONFLICT (id) DO NOTHING"
    )
    for type_id, name, r, g, b in _DEFAULT_TYPES:
        try:
            await conn.execute(insert_type, {"id": type_id, "name": name, "r": r, "g": g, "b": b})
        except Exception as exc:  # noqa: BLE001
            print(f"[migrations] avertissement seed type {type_id!r}: {exc}")

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
            print(f"[migrations] avertissement seed resource {res_id!r}: {exc}")

    # Au cas où "coins" existait déjà avant l'ajout de la colonne `protected`
    # (déploiement antérieur) : force le flag, ne dépend pas de l'ordre d'insertion.
    force_protected = text("UPDATE resources SET protected = TRUE WHERE id = :id")
    for res_id in _PROTECTED_RESOURCES:
        try:
            await conn.execute(force_protected, {"id": res_id})
        except Exception as exc:  # noqa: BLE001
            print(f"[migrations] avertissement protected {res_id!r}: {exc}")

    for table, values in _RECYCLE_DEFAULTS.items():
        update = text(
            f"UPDATE {table} SET recycle_value = :v WHERE id = :id AND recycle_value = 0"
        )
        for row_id, value in values.items():
            try:
                await conn.execute(update, {"id": row_id, "v": value})
            except Exception as exc:  # noqa: BLE001
                print(f"[migrations] avertissement recycle_value {table}.{row_id}: {exc}")

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
            print(f"[migrations] puissance calculée pour {len(rows)} carte(s) existante(s).")
    except Exception as exc:  # noqa: BLE001
        print(f"[migrations] avertissement backfill power: {exc}")
