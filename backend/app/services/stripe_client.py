"""
Appels à l'API Stripe via httpx (pas de dépendance au SDK) : création d'une
session de paiement Checkout, recherche de la commande d'un paiement remboursé
et vérification de la signature des webhooks.
"""

import hashlib
import hmac
import time
import uuid

import httpx
from fastapi import HTTPException

from app.config import settings

_STRIPE_URL = "https://api.stripe.com/v1"
_STRIPE_VERSION = "2026-05-27.dahlia"
SIGNATURE_TOLERANCE_S = 300
# Validité d'une page de paiement (30 min = minimum accepté par Stripe) : une
# commande abandonnée passe vite en « échouée » via checkout.session.expired.
CHECKOUT_EXPIRES_S = 30 * 60


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    return {"Stripe-Version": _STRIPE_VERSION, **(extra or {})}


def is_configured() -> bool:
    return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_WEBHOOK_SECRET)


async def create_checkout_session(
    *, order_id: int, product_name: str, amount_cents: int, currency: str, customer_email: str | None,
) -> tuple[str, str]:
    """Retourne (id de session Stripe, URL de paiement)."""
    base = settings.PUBLIC_APP_URL.rstrip("/")
    form = {
        "mode": "payment",
        "success_url": f"{base}/shop?premium=success",
        "cancel_url": f"{base}/shop?premium=cancel",
        "expires_at": str(int(time.time()) + CHECKOUT_EXPIRES_S),
        "client_reference_id": str(order_id),
        "metadata[order_id]": str(order_id),
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": currency,
        "line_items[0][price_data][unit_amount]": str(amount_cents),
        "line_items[0][price_data][product_data][name]": product_name,
    }
    if customer_email:
        form["customer_email"] = customer_email
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(
                f"{_STRIPE_URL}/checkout/sessions", data=form,
                auth=(settings.STRIPE_SECRET_KEY, ""),
                # Clé unique par appel : la même clé Stripe de test sert en local et en
                # production, et deux bases différentes peuvent avoir une commande n° 1.
                headers=_headers({"Idempotency-Key": f"order-{order_id}-{uuid.uuid4()}"}),
            )
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Le service de paiement est injoignable, réessaie plus tard.") from exc
    if res.status_code >= 300:
        raise HTTPException(502, "Le service de paiement a refusé la demande.")
    data = res.json()
    return data["id"], data["url"]


async def find_order_id_for_payment_intent(payment_intent_id: str) -> str | None:
    """Retrouve le n° de commande (metadata) de la session Checkout d'un paiement."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                f"{_STRIPE_URL}/checkout/sessions", params={"payment_intent": payment_intent_id, "limit": 1},
                auth=(settings.STRIPE_SECRET_KEY, ""), headers=_headers(),
            )
    except httpx.HTTPError:
        return None
    if res.status_code >= 300:
        return None
    sessions = res.json().get("data", [])
    return sessions[0].get("metadata", {}).get("order_id") if sessions else None


def verify_webhook_signature(payload: bytes, signature_header: str, secret: str, now: float | None = None) -> bool:
    """Vérifie l'en-tête Stripe-Signature (t=…,v1=…) : HMAC-SHA256 de « t.payload »."""
    parts: dict[str, list[str]] = {}
    for item in signature_header.split(","):
        key, _, value = item.strip().partition("=")
        parts.setdefault(key, []).append(value)
    try:
        timestamp = int(parts.get("t", [""])[0])
    except ValueError:
        return False
    if abs((now if now is not None else time.time()) - timestamp) > SIGNATURE_TOLERANCE_S:
        return False
    expected = hmac.new(secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, candidate) for candidate in parts.get("v1", []))
