"""
Petits correctifs de schéma et de données, idempotents, appliqués au démarrage
juste après `SQLModel.metadata.create_all` (qui ne crée que les tables
manquantes — pas les colonnes ajoutées sur une table déjà existante).

Chaque étape doit pouvoir être rejouée sans risque à chaque démarrage.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

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

# Ressources par défaut (recyclage / shop).
_DEFAULT_RESOURCES = [
    ("dust", "Poussière", "Obtenue en recyclant des cartes. Dépensable au shop."),
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
        "INSERT INTO resources (id, name, description) "
        "VALUES (:id, :name, :description) ON CONFLICT (id) DO NOTHING"
    )
    for res_id, name, description in _DEFAULT_RESOURCES:
        try:
            await conn.execute(insert_resource, {"id": res_id, "name": name, "description": description})
        except Exception as exc:  # noqa: BLE001
            print(f"[migrations] avertissement seed resource {res_id!r}: {exc}")

    for table, values in _RECYCLE_DEFAULTS.items():
        update = text(
            f"UPDATE {table} SET recycle_value = :v WHERE id = :id AND recycle_value = 0"
        )
        for row_id, value in values.items():
            try:
                await conn.execute(update, {"id": row_id, "v": value})
            except Exception as exc:  # noqa: BLE001
                print(f"[migrations] avertissement recycle_value {table}.{row_id}: {exc}")
