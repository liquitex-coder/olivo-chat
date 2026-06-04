"""FR-D1 — conversation + message API, auth-scoped and RLS-isolated."""
from __future__ import annotations

import httpx


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


async def test_create_then_list_conversation(client: httpx.AsyncClient) -> None:
    auth = await _signup(client, "olivo-a", "a@olivo.test")
    created = await client.post(
        "/api/v1/conversations", json={"title": "Table for 4?"}, headers=auth
    )
    assert created.status_code == 201
    conv_id = created.json()["id"]

    listed = await client.get("/api/v1/conversations", headers=auth)
    assert listed.status_code == 200
    assert [c["id"] for c in listed.json()] == [conv_id]


async def test_post_and_list_messages(client: httpx.AsyncClient) -> None:
    auth = await _signup(client, "olivo-a", "a@olivo.test")
    conv_id = (
        await client.post("/api/v1/conversations", json={"title": "Hi"}, headers=auth)
    ).json()["id"]

    posted = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"role": "user", "content": "Do you have gluten-free pasta?"},
        headers=auth,
    )
    assert posted.status_code == 201
    assert posted.json()["content"] == "Do you have gluten-free pasta?"

    msgs = await client.get(f"/api/v1/conversations/{conv_id}/messages", headers=auth)
    assert msgs.status_code == 200
    assert [m["content"] for m in msgs.json()] == ["Do you have gluten-free pasta?"]


async def test_other_tenant_cannot_read_messages(client: httpx.AsyncClient) -> None:
    auth_a = await _signup(client, "olivo-a", "a@olivo.test")
    conv_id = (
        await client.post("/api/v1/conversations", json={"title": "A"}, headers=auth_a)
    ).json()["id"]

    auth_b = await _signup(client, "olivo-b", "b@olivo.test")
    resp = await client.get(
        f"/api/v1/conversations/{conv_id}/messages", headers=auth_b
    )
    assert resp.status_code == 404  # RLS hides A's conversation from B


async def test_other_tenant_cannot_post_message(client: httpx.AsyncClient) -> None:
    auth_a = await _signup(client, "olivo-a", "a@olivo.test")
    conv_id = (
        await client.post("/api/v1/conversations", json={"title": "A"}, headers=auth_a)
    ).json()["id"]

    auth_b = await _signup(client, "olivo-b", "b@olivo.test")
    resp = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"role": "user", "content": "sneaky"},
        headers=auth_b,
    )
    assert resp.status_code == 404


async def test_message_in_unknown_conversation_is_404(client: httpx.AsyncClient) -> None:
    auth = await _signup(client, "olivo-a", "a@olivo.test")
    missing = "00000000-0000-0000-0000-000000000000"
    resp = await client.post(
        f"/api/v1/conversations/{missing}/messages",
        json={"role": "user", "content": "hello?"},
        headers=auth,
    )
    assert resp.status_code == 404
