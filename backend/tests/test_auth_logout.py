"""Step 3 — logout (refresh revocation)."""
from __future__ import annotations

import httpx


async def _signup(client: httpx.AsyncClient) -> tuple[str, str]:
    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "tenant_name": "Trattoria Olivo",
            "tenant_slug": "olivo",
            "email": "owner@olivo.test",
            "password": "correct horse battery",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    return body["access_token"], body["refresh_token"]


async def test_logout_revokes_refresh(client: httpx.AsyncClient) -> None:
    access, refresh = await _signup(client)
    out = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert out.status_code == 204
    # the revoked refresh can no longer be rotated
    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert reuse.status_code == 401


async def test_logout_requires_authentication(client: httpx.AsyncClient) -> None:
    _, refresh = await _signup(client)
    out = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh})
    assert out.status_code == 401
