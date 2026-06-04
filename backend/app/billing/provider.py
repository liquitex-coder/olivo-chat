"""Billing providers behind one interface.

`DemoBillingProvider` is the default: offline, no Stripe account, **no charges**. It
verifies the *same* HMAC-SHA256 scheme Stripe uses (`t=...,v1=...`), so webhook
handling is exercised for real without a network call. `StripeBillingProvider` wraps
the live SDK and is **not** wired in by default — live mode moves real money, so it
stays behind an explicit, cost-approved swap (SDK imported lazily).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Protocol, runtime_checkable

from app.config import settings


class WebhookVerificationError(Exception):
    """Raised when a webhook signature fails verification."""


def sign_payload(secret: str, payload: bytes, timestamp: int | None = None) -> str:
    """Produce a Stripe-style `t=<ts>,v1=<hmac>` signature header for `payload`."""
    ts = timestamp if timestamp is not None else int(time.time())
    signed = f"{ts}.".encode() + payload
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def _verify(secret: str, payload: bytes, header: str) -> dict:
    try:
        parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
        ts = parts["t"]
        provided = parts["v1"]
    except (KeyError, ValueError) as e:
        raise WebhookVerificationError("malformed signature header") from e
    expected = hmac.new(
        secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, provided):
        raise WebhookVerificationError("signature mismatch")
    try:
        return json.loads(payload.decode())
    except (ValueError, UnicodeDecodeError) as e:
        raise WebhookVerificationError("payload is not valid JSON") from e


@runtime_checkable
class BillingProvider(Protocol):
    def create_checkout_session(self, *, tenant_id: str, plan: str) -> str: ...
    def verify_webhook(self, *, payload: bytes, signature: str) -> dict: ...


class DemoBillingProvider:
    """Offline demo billing — deterministic checkout URL + real HMAC verification."""

    def __init__(self, webhook_secret: str) -> None:
        self._secret = webhook_secret

    def create_checkout_session(self, *, tenant_id: str, plan: str) -> str:
        return f"https://demo.stripe.local/checkout/{plan}?tenant={tenant_id}"

    def verify_webhook(self, *, payload: bytes, signature: str) -> dict:
        return _verify(self._secret, payload, signature)


class StripeBillingProvider:
    """Wraps the live Stripe SDK. Real charges → cost-gated, not wired by default."""

    def __init__(
        self, *, api_key: str, webhook_secret: str, price_ids: dict[str, str]
    ) -> None:
        self._api_key = api_key
        self._webhook_secret = webhook_secret
        self._price_ids = price_ids

    def create_checkout_session(self, *, tenant_id: str, plan: str) -> str:
        import stripe  # lazy: no key / no import cost at startup

        stripe.api_key = self._api_key
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": self._price_ids[plan], "quantity": 1}],
            metadata={"tenant_id": tenant_id, "plan": plan},
            success_url="https://example.test/ok",
            cancel_url="https://example.test/cancel",
        )
        return str(session.url)

    def verify_webhook(self, *, payload: bytes, signature: str) -> dict:
        import stripe

        try:
            return dict(
                stripe.Webhook.construct_event(
                    payload, signature, self._webhook_secret
                )
            )
        except Exception as e:  # noqa: BLE001 — normalise SDK errors to our type
            raise WebhookVerificationError(str(e)) from e


def get_billing_provider() -> BillingProvider:
    """FastAPI dependency. Demo default = offline, zero cost. Swapping in the Stripe
    provider is gated on explicit cost approval (live mode moves real money)."""
    return DemoBillingProvider(webhook_secret=settings.STRIPE_WEBHOOK_SECRET)
