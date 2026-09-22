"""
Pseudos et noms affichés : pas de caractères invisibles ni de nom réservé à
l'équipe (un joueur nommé « Administration » pourrait se faire passer pour
elle dans la messagerie, où seul le nom de l'expéditeur est affiché).
"""

import unicodedata

from fastapi import HTTPException

RESERVED_NAMES = {
    "admin", "administration", "administrateur", "administratrice", "moderateur", "moderatrice",
    "moderation", "modo", "support", "staff", "equipe", "cardegame", "systeme", "system",
}


def _skeleton(name: str) -> str:
    """Forme comparable : minuscules, sans accents, lettres et chiffres seulement."""
    decomposed = unicodedata.normalize("NFKD", name.casefold())
    return "".join(c for c in decomposed if c.isalnum() and not unicodedata.combining(c))


def ensure_not_reserved(name: str) -> None:
    if _skeleton(name) in RESERVED_NAMES:
        raise HTTPException(400, "Ce nom est réservé à l'équipe du jeu.")


def clean_display_name(raw: str) -> str:
    """Nom affiché nettoyé (espaces superflus retirés), ou 400 s'il n'est pas acceptable."""
    name = " ".join(raw.split())
    if not 1 <= len(name) <= 20:
        raise HTTPException(400, "Le nom affiché doit faire entre 1 et 20 caractères.")
    # Caractères de contrôle, invisibles (espaces de largeur nulle, inversion du
    # sens d'écriture…) ou privés : ils permettent d'imiter le nom d'un autre joueur.
    if any(unicodedata.category(c) in ("Cc", "Cf", "Co", "Cs") for c in name):
        raise HTTPException(400, "Le nom affiché contient des caractères non autorisés.")
    ensure_not_reserved(name)
    return name
