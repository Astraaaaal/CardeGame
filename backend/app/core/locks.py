"""
Verrous contre les actions simultanées (double réclamation, double dépense).

Chaque action (POST, PUT, PATCH, DELETE) d'un joueur prend un verrou Postgres
propre à ce joueur, gardé jusqu'à la fin de la transaction : deux requêtes du
même joueur envoyées en même temps passent l'une après l'autre, et la seconde
voit le résultat de la première. Sans effet sur SQLite (tests).
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Espace de clés des verrous « joueur » : pg_advisory_xact_lock(espace, id).
_USER_LOCK_SPACE = 1
# Au-delà, la requête abandonne (409, cf. app/main.py) au lieu d'attendre sans fin.
LOCK_TIMEOUT = "15s"

# Codes Postgres d'un conflit entre actions simultanées : interblocage, attente
# de verrou trop longue, sérialisation impossible. Rien à corriger, juste à réessayer.
CONFLICT_SQLSTATES = {"40P01", "55P03", "40001"}


def _is_postgres(session: AsyncSession) -> bool:
    return session.bind.dialect.name == "postgresql"


async def lock_user(session: AsyncSession, user_id: int) -> None:
    """Attend puis prend le verrou du joueur jusqu'au prochain commit/rollback."""
    if not _is_postgres(session):
        return
    await session.execute(text(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'"))
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:space, :id)"), {"space": _USER_LOCK_SPACE, "id": user_id},
    )
