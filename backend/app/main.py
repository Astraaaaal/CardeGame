"""
CardeGame API — Point d'entrée FastAPI.
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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api import auth, player, boosters, collection, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    print("[CardeGame API] Initialisation de la base de données...")
    await init_db()
    print("[CardeGame API] Prêt !")
    yield
    print("[CardeGame API] Arrêt.")


app = FastAPI(
    title="CardeGame API",
    description="Backend du jeu de collection de cartes CardeGame",
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

# ── Routes ──
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(player.router, prefix="/api/player", tags=["Player"])
app.include_router(boosters.router, prefix="/api/boosters", tags=["Boosters"])
app.include_router(collection.router, prefix="/api/collection", tags=["Collection"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
