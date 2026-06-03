"""Step 3 — refresh-token rotation."""
from __future__ import annotations

import httpx


async def _signup_get_refresh(client: httpx.AsyncClient) -> str:
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
    return resp.json()["refresh_token"]


async def test_refresh_rotates_to_new_tokens(client: httpx.AsyncClient) -> None:
    old_refresh = await _signup_get_refresh(client)
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"] != old_refresh  # rotated


async def test_old_refresh_is_revoked_after_rotation(client: httpx.AsyncClient) -> None:
    old_refresh = await _signup_get_refresh(client)
    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200
    # reusing the now-revoked old refresh must fail
    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse.status_code == 401


async def test_new_refresh_chains(client: httpx.AsyncClient) -> None:
    old_refresh = await _signup_get_refresh(client)
    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    new_refresh = first.json()["refresh_token"]
    second = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert second.status_code == 200
    assert second.json()["refresh_token"] not in (old_refresh, new_refresh)
