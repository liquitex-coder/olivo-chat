"""Step 3 — signup endpoint."""
from __future__ import annotations

import httpx


def _signup_body(slug: str = "trattoria-olivo", email: str = "owner@olivo.test") -> dict:
    return {
        "tenant_name": "Trattoria Olivo",
        "tenant_slug": slug,
        "email": email,
        "password": "correct horse battery",
    }


async def test_signup_creates_tenant_and_returns_tokens(client: httpx.AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/signup", json=_signup_body())
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


async def test_signup_duplicate_slug_conflicts(client: httpx.AsyncClient) -> None:
    first = await client.post("/api/v1/auth/signup", json=_signup_body())
    assert first.status_code == 201
    dup = await client.post(
        "/api/v1/auth/signup",
        json=_signup_body(slug="trattoria-olivo", email="other@olivo.test"),
    )
    assert dup.status_code == 409


async def test_signup_same_email_different_tenant_is_allowed(
    client: httpx.AsyncClient,
) -> None:
    # (tenant_id, email) is unique — the same email under a different tenant is fine.
    a = await client.post("/api/v1/auth/signup", json=_signup_body(slug="olivo-a"))
    b = await client.post("/api/v1/auth/signup", json=_signup_body(slug="olivo-b"))
    assert a.status_code == 201
    assert b.status_code == 201


async def test_signup_short_password_rejected(client: httpx.AsyncClient) -> None:
    body = _signup_body()
    body["password"] = "short"  # < 8
    resp = await client.post("/api/v1/auth/signup", json=body)
    assert resp.status_code == 422
