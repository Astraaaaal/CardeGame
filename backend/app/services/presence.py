"""
Statut "en ligne" — dérivé de User.last_seen, rafraîchi à chaque appel API
authentifié (cf. core/dependencies.py). Le client interroge l'état des
échanges toutes les 4 s tant que l'onglet est visible, donc un joueur actif
réécrit last_seen au plus toutes les LAST_SEEN_THROTTLE_S secondes.
"""

from datetime import datetime, timedelta

from app.models.user import User

ONLINE_THRESHOLD_S = 30
# Doit rester nettement sous le seuil, sinon un joueur actif clignoterait hors ligne.
LAST_SEEN_THROTTLE_S = 10


def is_online(user: User) -> bool:
    return bool(user.last_seen and datetime.utcnow() - user.last_seen < timedelta(seconds=ONLINE_THRESHOLD_S))
