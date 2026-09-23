"""
Limites d'achat réglables, partagées par la boutique (offres en ressources)
et la boutique premium (produits en euros) : aucune, par jour, par semaine,
par mois, ou une fois pour toutes ("account").
"""

from datetime import date, datetime, timedelta

PERIOD_NONE = "none"
PERIOD_DAY = "day"
PERIOD_WEEK = "week"
PERIOD_MONTH = "month"
PERIOD_ACCOUNT = "account"

_LABELS = {
    PERIOD_DAY: "aujourd'hui",
    PERIOD_WEEK: "cette semaine",
    PERIOD_MONTH: "ce mois",
    PERIOD_ACCOUNT: "au total",
}


def window_start(period: str, today: date | None = None) -> datetime | None:
    """Début de la période en cours ; None si la limite porte sur tout l'historique.
    En UTC, comme les horodatages d'achat (sinon un achat fait juste après
    minuit UTC n'était plus compté)."""
    today = today or datetime.utcnow().date()
    if period == PERIOD_DAY:
        start = today
    elif period == PERIOD_WEEK:
        start = today - timedelta(days=today.weekday())
    elif period == PERIOD_MONTH:
        start = today.replace(day=1)
    else:
        return None
    return datetime.combine(start, datetime.min.time())


def label(period: str) -> str:
    return _LABELS.get(period, "")


async def account_start(session) -> datetime | None:
    """Début de la période « une fois par compte » : la dernière remise à zéro,
    ou None si le jeu n'en a jamais connu. L'historique d'achat n'est jamais
    effacé — c'est seulement le décompte qui repart."""
    from app.models.game_config import GameConfig

    config = await session.get(GameConfig, 1)
    return config.last_reset_at if config else None
