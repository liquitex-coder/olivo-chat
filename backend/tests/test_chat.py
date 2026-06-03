"""FR-D2 — chat reply generation (mock provider; no live Claude call, no cost)."""
from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest

from app.chat import DemoChatProvider, get_chat_provider
from app.main import app


class _StubProvider:
    """Deterministic test double — stands in for any ChatProvider."""

    async def reply(self, *, user_message: str, history: list[str]) -> str:
        return f"stub reply to: {user_message}"


@pytest.fixture
def stub_provider() -> Iterator[None]:
    app.dependency_overrides[get_chat_provider] = lambda: _StubProvider()
    yield
    app.dependency_overrides.pop(get_chat_provider, None)


async def _signup(client: httpx.AsyncClient, slug: str, email: str) -> dict[str, str]:
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
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _new_conversation(client: httpx.AsyncClient, auth: dict[str, str]) -> str:
    resp = await client.post("/api/v1/conversations", json={"title": "Chat"}, headers=auth)
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_chat_persists_user_and_assistant(
    client: httpx.AsyncClient, stub_provider: None
) -> None:
    auth = await _signup(client, "olivo-a", "a@olivo.test")
    conv_id = await _new_conversation(client, auth)

    resp = await client.post(
        f"/api/v1/conversations/{conv_id}/chat",
        json={"content": "Do you take reservations?"},
        headers=auth,
    )
    assert resp.status_code == 201
    turns = resp.json()
    assert [m["role"] for m in turns] == ["user", "assistant"]
    assert turns[1]["content"] == "stub reply to: Do you take reservations?"

    # both turns are persisted and visible via the messages endpoint
    msgs = await client.get(f"/api/v1/conversations/{conv_id}/messages", headers=auth)
    assert [m["role"] for m in msgs.json()] == ["user", "assistant"]


async def test_chat_on_foreign_conversation_is_404(
    client: httpx.AsyncClient, stub_provider: None
) -> None:
    auth_a = await _signup(client, "olivo-a", "a@olivo.test")
    conv_id = await _new_conversation(client, auth_a)
    auth_b = await _signup(client, "olivo-b", "b@olivo.test")

    resp = await client.post(
        f"/api/v1/conversations/{conv_id}/chat",
        json={"content": "sneaky"},
        headers=auth_b,
    )
    assert resp.status_code == 404


async def test_demo_provider_is_deterministic_and_offline() -> None:
    provider = DemoChatProvider()
    first = await provider.reply(user_message="Hi", history=[])
    second = await provider.reply(user_message="Hi", history=[])
    assert first == second
    assert "Hi" in first
