"""
Database engine et session factory — async avec asyncpg.
"""

from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings


def _prepare_url(raw_url: str) -> tuple[str, dict]:
    """
    Normalise la DATABASE_URL pour asyncpg et en déduit les connect_args.

    - `postgresql://`            → `postgresql+asyncpg://`
    - `sslmode=require` (libpq)  → retiré de l'URL, converti en `ssl=True` (asyncpg)
    - hôte distant (non-local)   → SSL activé par défaut (Neon, Render, etc.)
    """
    url = raw_url
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))

    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)  # param libpq non géré par asyncpg

    is_local = parts.hostname in ("localhost", "127.0.0.1", "::1")
    want_ssl = (sslmode not in (None, "disable", "allow")) or not is_local

    url = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
    connect_args = {"ssl": True} if want_ssl else {}
    return url, connect_args


_url, _connect_args = _prepare_url(settings.DATABASE_URL)

engine = create_async_engine(
    _url,
    echo=False,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,     # rejette les connexions coupées par Neon après inactivité
    pool_recycle=300,
    connect_args=_connect_args,
)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Crée toutes les tables au démarrage (dev only — utiliser Alembic en prod)."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncSession:  # type: ignore
    """Dependency injection pour les routes FastAPI."""
    async with async_session() as session:
        yield session
