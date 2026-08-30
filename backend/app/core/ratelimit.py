"""
Rate limiting léger, en mémoire, par IP + chemin.
Suffisant pour une instance unique (Render free). Pas de dépendance externe.
"""

import time
from collections import defaultdict

from fastapi import Request, HTTPException, status

_hits: dict[str, list[float]] = defaultdict(list)
_last_gc = 0.0


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _gc(now: float, window_s: int) -> None:
    """Purge occasionnelle des clés dont tous les hits ont expiré."""
    global _last_gc
    if now - _last_gc < 300 or len(_hits) < 500:
        return
    _last_gc = now
    for key in list(_hits):
        if all(now - t >= window_s for t in _hits[key]):
            del _hits[key]


def rate_limit(max_calls: int, window_s: int = 60):
    """Dépendance FastAPI : au plus `max_calls` requêtes / `window_s` s par IP."""

    async def _dep(request: Request) -> None:
        now = time.time()
        _gc(now, window_s)
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
