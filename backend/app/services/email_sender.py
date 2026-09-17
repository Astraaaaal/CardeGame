"""
Envoi d'e-mails et synchronisation de la newsletter via l'API Brevo.

Sans BREVO_API_KEY (dev, tests), rien ne part : le contenu est écrit dans les
logs, ce qui permet de récupérer un lien ou un code en local.
"""

import html
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_BREVO_URL = "https://api.brevo.com/v3"


def _headers() -> dict:
    return {"api-key": settings.BREVO_API_KEY, "accept": "application/json", "content-type": "application/json"}


def _layout(title: str, body_html: str) -> str:
    return (
        "<div style=\"font-family:Arial,sans-serif;max-width:480px;margin:auto;color:#1a1a2e\">"
        f"<h2 style=\"color:#4f46e5\">{html.escape(title)}</h2>{body_html}"
        "<p style=\"color:#888;font-size:12px;margin-top:32px\">CardeGame — si tu n'es pas à l'origine "
        "de cette demande, ignore simplement cet e-mail.</p></div>"
    )


async def send_email(to: str, subject: str, title: str, body_html: str) -> None:
    """Envoie un e-mail transactionnel. Ne lève pas : un échec d'envoi est journalisé."""
    content = _layout(title, body_html)
    if not settings.BREVO_API_KEY:
        logger.info("[e-mail non envoyé — BREVO_API_KEY absente] à=%s objet=%s\n%s", to, subject, content)
        return
    payload = {
        "sender": {"name": settings.EMAIL_SENDER_NAME, "email": settings.EMAIL_SENDER_ADDRESS},
        "to": [{"email": to}],
        "subject": subject,
        "htmlContent": content,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(f"{_BREVO_URL}/smtp/email", json=payload, headers=_headers())
        if res.status_code >= 300:
            logger.error("Brevo send_email %s : %s", res.status_code, res.text)
    except httpx.HTTPError as exc:
        logger.error("Brevo send_email injoignable : %s", exc)


async def sync_newsletter(email: str | None, subscribed: bool, username: str = "") -> None:
    """Ajoute ou retire l'adresse de la liste newsletter Brevo (si configurée)."""
    list_id_raw = settings.BREVO_NEWSLETTER_LIST_ID.strip()
    if not email or not settings.BREVO_API_KEY or not list_id_raw.isdigit() or int(list_id_raw) == 0:
        return
    list_id = int(list_id_raw)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if subscribed:
                res = await client.post(f"{_BREVO_URL}/contacts", headers=_headers(), json={
                    "email": email, "listIds": [list_id], "updateEnabled": True,
                    "attributes": {"PSEUDO": username},
                })
            else:
                res = await client.post(
                    f"{_BREVO_URL}/contacts/lists/{list_id}/contacts/remove",
                    headers=_headers(), json={"emails": [email]},
                )
        # 400 "contact déjà absent de la liste" est normal à la désinscription.
        if res.status_code >= 300 and not (not subscribed and res.status_code == 400):
            logger.error("Brevo newsletter %s : %s", res.status_code, res.text)
    except httpx.HTTPError as exc:
        logger.error("Brevo newsletter injoignable : %s", exc)
