"""
Fixtures de test — base SQLite en mémoire, isolée de la vraie BDD (Neon,
partagée dev/prod, cf. docs/DEPLOY.md). Chaque test reçoit sa propre base
vide : aucune donnée réelle n'est jamais lue ni modifiée en testant.
"""

import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

import app.main  # noqa: F401 - importe toutes les routes -> enregistre tous les modèles dans SQLModel.metadata

from app.models.user import User
from app.core.security import hash_password


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        yield s

    await engine.dispose()


async def make_user(session: AsyncSession, username: str = "test_user") -> User:
    user = User(username=username, display_name=username, password_hash=hash_password("password123"))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
