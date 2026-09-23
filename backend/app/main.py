"""
A Card Game — API, point d'entrée FastAPI.
"""

# Force UTF-8 sur stdout/stderr : sinon un print() contenant un caractère non
# présent dans cp1252 (ex. "✓") fait planter la requête sous Windows.
import sys as _sys

for _stream in (_sys.stdout, _sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError

from app.config import settings
from app.core.locks import CONFLICT_SQLSTATES
from app.core.logging_config import setup_logging, logger
from app.core.ratelimit import check_global_rate_limit, client_ip
from app.database import init_db
from app.api import auth, player, players, boosters, collection, admin, admin_content, types, shop, friends, leaderboard, trades, messages, progression, support, premium, activities, guilds, favorites

setup_logging()
settings.check_production_secrets()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    logger.info("Initialisation de la base de données...")
    try:
        await init_db()
        logger.info("Prêt !")
    except Exception:  # BDD injoignable (réseau qui filtre Postgres, Neon suspendu…)
        logger.exception("BDD injoignable au démarrage.")
        logger.warning("L'API démarre quand même ; les routes BDD échoueront "
                        "tant que la connexion n'est pas rétablie (réseau / Neon).")
    yield
    logger.info("Arrêt.")


app = FastAPI(
    title="A Card Game — API",
    description="Backend du jeu de collection de cartes A Card Game",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Limite globale de requêtes (filet de sécurité en plus des limites par
# route, cf. app/core/ratelimit.py) — couvre toute l'API, protège contre un
# client qui boucle en erreur ou un pic de trafic sur cette instance unique.
@app.middleware("http")
async def global_rate_limit_middleware(request: Request, call_next):
    if request.url.path != "/api/health" and not check_global_rate_limit(client_ip(request)):
        return JSONResponse(status_code=429, content={"detail": "Trop de requêtes. Réessaie dans un instant."})
    return await call_next(request)


# ── Routes ──
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(player.router, prefix="/api/player", tags=["Player"])
app.include_router(players.router, prefix="/api/players", tags=["Joueurs"])
app.include_router(boosters.router, prefix="/api/boosters", tags=["Boosters"])
app.include_router(collection.router, prefix="/api/collection", tags=["Collection"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(admin_content.router, prefix="/api/admin/content", tags=["Admin — Contenu"])
app.include_router(types.router, prefix="/api/types", tags=["Types"])
app.include_router(shop.router, prefix="/api/shop", tags=["Shop"])
app.include_router(friends.router, prefix="/api/friends", tags=["Amis"])
app.include_router(leaderboard.router, prefix="/api/leaderboard", tags=["Classement"])
app.include_router(trades.router, prefix="/api/trade-sessions", tags=["Échanges"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messagerie"])
app.include_router(messages.admin_router, prefix="/api/admin/messages", tags=["Admin — Messagerie"])
app.include_router(progression.router, prefix="/api/progression", tags=["Progression"])
app.include_router(support.router, prefix="/api/support", tags=["Support"])
app.include_router(support.admin_router, prefix="/api/admin/bug-reports", tags=["Admin — Support"])
app.include_router(premium.router, prefix="/api/premium", tags=["Boutique premium"])
app.include_router(premium.admin_router, prefix="/api/admin/premium", tags=["Admin — Premium"])
app.include_router(activities.router, prefix="/api/activities", tags=["Activités"])
app.include_router(activities.admin_router, prefix="/api/admin/activities", tags=["Admin — Activités"])
app.include_router(guilds.router, prefix="/api/guilds", tags=["Guildes"])
app.include_router(favorites.router, prefix="/api/favorites", tags=["Favoris"])


@app.exception_handler(DBAPIError)
async def database_error_handler(request: Request, exc: DBAPIError):
    """Deux actions simultanées sur les mêmes données : 409 « réessaie » plutôt qu'une erreur 500."""
    code = getattr(exc.orig, "pgcode", None) or getattr(exc.orig, "sqlstate", None)
    if code in CONFLICT_SQLSTATES:
        logger.warning("Actions simultanées (%s) sur %s %s", code, request.method, request.url.path)
        return JSONResponse(status_code=409, content={"detail": "Une autre action est en cours, réessaie dans un instant."})
    logger.exception("Erreur de base de données sur %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur."})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Erreur non gérée sur %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur."})


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
