"""Step 3 — login endpoint."""
from __future__ import annotations

import httpx

from app.auth.jwt_tokens import decode_token

_EMAIL = "owner@olivo.test"
_PASSWORD = "correct horse battery"


async def _signup(client: httpx.AsyncClient, slug: str = "olivo") -> None:
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "tenant_name": "Trattoria Olivo",
            "tenant_slug": slug,
            "email": _EMAIL,
            "password": _PASSWORD,
        },
    )
    assert resp.status_code == 201


async def test_login_success_returns_tokens(client: httpx.AsyncClient) -> None:
    await _signup(client)
    resp = await client.post(
        "/api/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]


async def test_login_wrong_password_is_401(client: httpx.AsyncClient) -> None:
    await _signup(client)
    resp = await client.post(
        "/api/v1/auth/login", json={"email": _EMAIL, "password": "wrong-password"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


async def test_login_unknown_email_is_401(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@olivo.test", "password": _PASSWORD}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


async def test_login_access_token_claims(client: httpx.AsyncClient) -> None:
    await _signup(client)
    resp = await client.post(
        "/api/v1/auth/login", json={"email": _EMAIL, "password": _PASSWORD}
    )
    claims = decode_token(resp.json()["access_token"])
    assert claims["typ"] == "access"
    assert claims["sub"] and claims["tid"]
    assert "exp" in claims and "iat" in claims
