"""
E-mail de compte (app/services/account_email.py) : inscription avec e-mail,
connexion par pseudo ou e-mail, confirmation par lien, récupération de mot
de passe par code (tentatives et envois plafonnés).
"""

import re

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.models.token import RefreshToken
from app.services import account_email
from app.services.auth_service import AuthService
from app.core.security import verify_password

auth = AuthService()


@pytest.fixture
def outbox(monkeypatch):
    sent: list[dict] = []

    async def fake_send(to, subject, title, body_html):
        sent.append({"to": to, "subject": subject, "body": body_html})

    async def fake_sync(*args, **kwargs):
        return None

    monkeypatch.setattr(account_email, "send_email", fake_send)
    monkeypatch.setattr(account_email, "sync_newsletter", fake_sync)
    return sent


def _token_from(mail: dict) -> str:
    return re.search(r"token=([\w\-]+)", mail["body"]).group(1)


def _code_from(mail: dict) -> str:
    return re.search(r">(\d{6})<", mail["body"]).group(1)


async def test_register_requires_valid_unique_email_and_login_accepts_it(session, outbox):
    user = await auth.register(session, "alice", "secret1", "  Alice@Example.COM ")
    assert user.email == "alice@example.com" and user.email_verified_at is None

    with pytest.raises(HTTPException) as exc:
        await auth.register(session, "alice2", "secret1", "alice@example.com")
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException):
        await auth.register(session, "bob", "secret1", "pas-un-email")

    assert (await auth.login(session, "ALICE@example.com", "secret1"))["access_token"]
    assert (await auth.login(session, "alice", "secret1"))["access_token"]


async def test_verification_link_confirms_and_dies_when_email_changes(session, outbox):
    user = await auth.register(session, "alice", "secret1", "alice@example.com")
    await account_email.send_verification(session, user)
    old_token = _token_from(outbox[-1])

    await account_email.change_email(session, user, "new@example.com", "secret1")
    with pytest.raises(HTTPException):
        await account_email.confirm_email(session, old_token)  # lien de l'ancienne adresse

    confirmed = await account_email.confirm_email(session, _token_from(outbox[-1]))
    assert confirmed.email == "new@example.com" and confirmed.email_verified_at is not None


async def test_password_reset_needs_verified_email_and_limits_attempts(session, outbox):
    user = await auth.register(session, "alice", "secret1", "alice@example.com")
    await auth.login(session, "alice", "secret1")

    await account_email.request_password_reset(session, "alice")
    assert outbox == []  # adresse pas encore confirmée : aucun code

    await account_email.send_verification(session, user)
    await account_email.confirm_email(session, _token_from(outbox[-1]))
    await account_email.request_password_reset(session, "alice@example.com")
    code = _code_from(outbox[-1])

    wrong = "000000" if code != "000000" else "111111"
    for _ in range(account_email.RESET_CODE_MAX_ATTEMPTS):
        with pytest.raises(HTTPException):
            await account_email.confirm_password_reset(session, "alice", wrong, "newpass")
    with pytest.raises(HTTPException):  # bon code, mais trop de tentatives
        await account_email.confirm_password_reset(session, "alice", code, "newpass")

    await account_email.request_password_reset(session, "alice")
    await account_email.confirm_password_reset(session, "alice", _code_from(outbox[-1]), "newpass")
    await session.refresh(user)
    assert verify_password("newpass", user.password_hash)
    tokens = (await session.execute(select(RefreshToken).where(RefreshToken.user_id == user.id))).scalars().all()
    assert tokens == []  # toutes les sessions déconnectées


async def test_password_reset_codes_are_capped_per_hour(session, outbox):
    user = await auth.register(session, "alice", "secret1", "alice@example.com")
    await account_email.send_verification(session, user)
    await account_email.confirm_email(session, _token_from(outbox[-1]))
    outbox.clear()

    for _ in range(account_email.RESET_CODES_PER_HOUR + 3):
        await account_email.request_password_reset(session, "alice")
    assert len(outbox) == account_email.RESET_CODES_PER_HOUR
