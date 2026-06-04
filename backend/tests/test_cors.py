"""CORS is wired from CORS_ORIGINS so the Vite frontends can call the API."""
from __future__ import annotations

import httpx


async def test_cors_allows_configured_origin(client: httpx.AsyncClient) -> None:
    resp = await client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


async def test_cors_omits_unconfigured_origin(client: httpx.AsyncClient) -> None:
    resp = await client.get("/health", headers={"Origin": "https://evil.example"})
    assert resp.headers.get("access-control-allow-origin") != "https://evil.example"
