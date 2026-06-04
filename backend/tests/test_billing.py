"""FR-D3 — billing (test-mode/offline; no Stripe account, no charges)."""
from __future__ import annotations

import json

import httpx

from app.auth.jwt_tokens import decode_token
from app.billing.provider import sign_payload
from app.billing.service import has_at_least
from app.config import settings


async def _signup(client: httpx.AsyncClient, slug: str, email: str) -> tuple[dict, str]:
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "tenant_name": f"Tenant {slug}",
            "tenant_slug": slug,
            "email": email,
            "password": "correct horse battery",
        },
    )
    assert resp.status_code == 201
    access = resp.json()["access_token"]
    tenant_id = decode_token(access)["tid"]
    return {"Authorization": f"Bearer {access}"}, tenant_id


def _signed_upgrade_event(tenant_id: str, plan: str) -> tuple[bytes, str]:
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"metadata": {"tenant_id": tenant_id, "plan": plan}}},
    }
    payload = json.dumps(event).encode()
    signature = sign_payload(settings.STRIPE_WEBHOOK_SECRET, payload)
    return payload, signature


async def test_checkout_returns_url(client: httpx.AsyncClient) -> None:
    auth, tenant_id = await _signup(client, "olivo-a", "a@olivo.test")
    resp = await client.post("/api/v1/billing/checkout", json={"plan": "pro"}, headers=auth)
    assert resp.status_code == 200
    url = resp.json()["checkout_url"]
    assert "pro" in url and tenant_id in url


async def test_plan_defaults_to_free(client: httpx.AsyncClient) -> None:
    auth, _ = await _signup(client, "olivo-a", "a@olivo.test")
    resp = await client.get("/api/v1/billing/plan", headers=auth)
    assert resp.status_code == 200
    assert resp.json()["plan"] == "free"


async def test_webhook_upgrades_plan(client: httpx.AsyncClient) -> None:
    auth, tenant_id = await _signup(client, "olivo-a", "a@olivo.test")
    payload, signature = _signed_upgrade_event(tenant_id, "pro")
    hook = await client.post(
        "/api/v1/billing/webhook",
        content=payload,
        headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
    )
    assert hook.status_code == 200
    assert hook.json() == {"received": True, "updated": True}

    plan = await client.get("/api/v1/billing/plan", headers=auth)
    assert plan.json()["plan"] == "pro"


async def test_webhook_rejects_bad_signature(client: httpx.AsyncClient) -> None:
    _, tenant_id = await _signup(client, "olivo-a", "a@olivo.test")
    payload, _ = _signed_upgrade_event(tenant_id, "pro")
    resp = await client.post(
        "/api/v1/billing/webhook",
        content=payload,
        headers={"Stripe-Signature": "t=1,v1=deadbeef", "Content-Type": "application/json"},
    )
    assert resp.status_code == 400


async def test_premium_gated_by_plan(client: httpx.AsyncClient) -> None:
    auth, tenant_id = await _signup(client, "olivo-a", "a@olivo.test")
    # free plan is blocked
    blocked = await client.get("/api/v1/billing/premium", headers=auth)
    assert blocked.status_code == 402

    payload, signature = _signed_upgrade_event(tenant_id, "business")
    await client.post(
        "/api/v1/billing/webhook",
        content=payload,
        headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
    )
    allowed = await client.get("/api/v1/billing/premium", headers=auth)
    assert allowed.status_code == 200
    assert allowed.json()["plan"] == "business"


def test_plan_ranking_is_ordered() -> None:
    assert has_at_least("business", "pro")
    assert has_at_least("pro", "pro")
    assert not has_at_least("free", "pro")
