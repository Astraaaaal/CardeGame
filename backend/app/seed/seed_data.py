"""
Seed — Migration des données JSON existantes vers PostgreSQL.
Lit les fichiers assets/data/*.json et les insère dans la BDD.
"""

import json
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.reference import Set, Rarity, Quality, Specialty, Jewelry
from app.models.character import Character, CharacterSet
from app.models.booster import Booster
from app.models.user import User
from app.models.card import UserCard
from app.core.security import hash_password

# Chemin vers les données JSON (relatif au workspace root)
# En production, ces fichiers sont copiés ou montés
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "assets", "data",
)
SAVES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "saves",
)


def _load_json(filename: str, key: str) -> list:
    """Charge un fichier JSON et retourne la liste sous la clé donnée."""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"[Seed] ATTENTION: {filepath} introuvable!")
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(key, [])


def _load_json_raw(filepath: str) -> dict:
    """Charge un fichier JSON brut."""
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


async def seed_reference_data(session: AsyncSession):
    """
    Migration 1:1 de tous les JSON de référence vers PostgreSQL.
    Idempotent : vérifie si les données existent déjà.
    """
    # Vérifier si déjà seedé
    result = await session.execute(select(Set))
    if result.scalars().first():
        print("[Seed] Données déjà présentes, skip.")
        return

    print(f"[Seed] Chargement depuis {DATA_DIR}")

    # ── Sets ──
    for s in _load_json("sets.json", "sets"):
        session.add(Set(
            id=s["id"],
            name=s["name"],
            description=s.get("description", ""),
        ))
    print("[Seed] Sets insérés")

    # ── Rarities ──
    for r in _load_json("rarities.json", "rarities"):
        color = r.get("color", [200, 200, 200])
        label = r.get("label_color", [200, 200, 200])
        session.add(Rarity(
            id=r["id"],
            name=r["name"],
            weight=r["weight"],
            color_r=color[0], color_g=color[1], color_b=color[2],
            label_color_r=label[0], label_color_g=label[1], label_color_b=label[2],
        ))
    print("[Seed] Rarities insérées")

    # ── Qualities ──
    for q in _load_json("qualities.json", "qualities"):
        session.add(Quality(
            id=q["id"],
            name=q["name"],
            weight=q["weight"],
            filter_type=q.get("filter", "none"),
            description=q.get("description", ""),
        ))
    print("[Seed] Qualities insérées")

    # ── Specialties ──
    for s in _load_json("specialties.json", "specialties"):
        session.add(Specialty(
            id=s["id"],
            name=s["name"],
            weight=s["weight"],
            border_type=s.get("border", "default"),
            effect=s.get("effect", "none"),
            description=s.get("description", ""),
        ))
    print("[Seed] Specialties insérées")

    # ── Jewelries ──
    for j in _load_json("jewelries.json", "jewelries"):
        color = j.get("color", [100, 100, 120])
        session.add(Jewelry(
            id=j["id"],
            name=j["name"],
            weight=j["weight"],
            color_r=color[0], color_g=color[1], color_b=color[2],
            description=j.get("description", ""),
        ))
    print("[Seed] Jewelries insérées")

    # Flush pour que les FK soient disponibles
    await session.flush()

    # ── Characters + CharacterSets ──
    for c in _load_json("characters.json", "characters"):
        session.add(Character(
            id=c["id"],
            name=c["name"],
            description=c.get("description", ""),
            type=c.get("type", "Normal"),
            gen=c.get("gen", 1),
            image_url=c.get("image", ""),
        ))
        for set_id, weight in c.get("weight_per_set", {}).items():
            session.add(CharacterSet(
                character_id=c["id"],
                set_id=set_id,
                weight=weight,
            ))
    print("[Seed] Characters insérés")

    # ── Boosters ──
    for b in _load_json("boosters.json", "boosters"):
        session.add(Booster(
            id=b["id"],
            name=b["name"],
            set_id=b["set"],
            cards_count=b.get("cards_count", 5),
            price=b["price"],
            guaranteed_rare=b.get("guaranteed_rare", False),
            description=b.get("description", ""),
        ))
    print("[Seed] Boosters insérés")

    await session.commit()
    print("[Seed] Toutes les données de référence insérées avec succès !")


async def migrate_player_saves(session: AsyncSession) -> int:
    """
    Migre les sauvegardes joueurs depuis accounts.json + player_save.json.
    Les mots de passe SHA-256 ne sont pas migrables → mot de passe temporaire.
    Retourne le nombre de joueurs migrés.
    """
    accounts_file = os.path.join(SAVES_DIR, "accounts.json")
    accounts = _load_json_raw(accounts_file)

    if not accounts:
        print("[Migration] Aucun compte à migrer.")
        return 0

    count = 0
    for username, data in accounts.items():
        # Vérifier si déjà migré
        result = await session.execute(
            select(User).where(User.username == username)
        )
        if result.scalar_one_or_none():
            print(f"[Migration] {username} déjà migré, skip.")
            continue

        # Créer le user avec un mot de passe temporaire
        # (l'ancien hash SHA-256 n'est pas compatible bcrypt)
        user = User(
            username=username,
            display_name=data.get("display_name", username),
            password_hash=hash_password("reset_required"),
            coins=500,
            login_streak=data.get("login_streak", 0),
        )
        session.add(user)
        await session.flush()  # Pour obtenir user.id

        # Charger le player_save.json
        save_path = os.path.join(SAVES_DIR, username, "player_save.json")
        if os.path.exists(save_path):
            with open(save_path, "r", encoding="utf-8") as f:
                save = json.load(f)

            user.coins = save.get("coins", 500)
            user.packs_opened = save.get("packs_opened", 0)
            user.total_cards = save.get("total_cards_obtained", 0)

            # Migrer les cartes
            for card_data in save.get("collection", []):
                session.add(UserCard(
                    user_id=user.id,
                    character_id=card_data.get("character_id", ""),
                    set_id=card_data.get("set_id", ""),
                    rarity_id=card_data.get("rarity_id", ""),
                    quality_id=card_data.get("quality_id", ""),
                    specialty_id=card_data.get("specialty_id", ""),
                    jewelry_id=card_data.get("jewelry_id", "none"),
                    drop_probability=card_data.get("drop_probability", 0),
                ))

        count += 1
        print(f"[Migration] {username} migré ({user.coins} coins, "
              f"{user.total_cards} cartes)")

    await session.commit()
    print(f"[Migration] {count} joueur(s) migré(s) au total !")
    return count
