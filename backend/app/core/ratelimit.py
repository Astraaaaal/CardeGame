"""
Rate limiting léger, en mémoire, par IP + chemin.
Suffisant pour une instance unique (Render free). Pas de dépendance externe.
"""

import time
from collections import defaultdict

from fastapi import Request, HTTPException, status

_hits: dict[str, list[float]] = defaultdict(list)
_last_gc_by_store: dict[str, float] = {}


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _gc(store: dict[str, list[float]], now: float, window_s: int, store_key: str) -> None:
    """Purge occasionnelle des clés dont tous les hits ont expiré."""
    last = _last_gc_by_store.get(store_key, 0.0)
    if now - last < 300 or len(store) < 500:
        return
    _last_gc_by_store[store_key] = now
    for key in list(store):
        if all(now - t >= window_s for t in store[key]):
            del store[key]


def rate_limit(max_calls: int, window_s: int = 60):
    """Dépendance FastAPI : au plus `max_calls` requêtes / `window_s` s par IP, sur CETTE route."""

    async def _dep(request: Request) -> None:
        now = time.time()
        _gc(_hits, now, window_s, "per_route")
        key = f"{request.url.path}:{_client_ip(request)}"
        recent = [t for t in _hits[key] if now - t < window_s]
        if len(recent) >= max_calls:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de requêtes. Réessaie dans un instant.",
            )
        recent.append(now)
        _hits[key] = recent

    return _dep


# ── Limite globale (filet de sécurité, en plus des limites par route
# ci-dessus) : couvre TOUTES les routes, y compris celles qui n'ont pas de
# `rate_limit(...)` explicite — protège contre un client qui boucle en
# erreur, un bot, ou simplement un pic de trafic, sur cette instance unique.
_global_hits: dict[str, list[float]] = defaultdict(list)
GLOBAL_MAX_CALLS = 120
GLOBAL_WINDOW_S = 60


def check_global_rate_limit(ip: str) -> bool:
    """Retourne False si `ip` dépasse la limite globale (à appeler depuis le middleware)."""
    now = time.time()
    _gc(_global_hits, now, GLOBAL_WINDOW_S, "global")
    recent = [t for t in _global_hits[ip] if now - t < GLOBAL_WINDOW_S]
    if len(recent) >= GLOBAL_MAX_CALLS:
        return False
    recent.append(now)
    _global_hits[ip] = recent
    return True


def client_ip(request: Request) -> str:
    return _client_ip(request)
