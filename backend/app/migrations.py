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
