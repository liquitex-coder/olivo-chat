"""Step 3 — protected endpoint proving JWT-armed RLS isolation (the crux)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import jwt

from app.auth.jwt_tokens import decode_token
from app.config import settings
from app.db import async_session_factory, set_tenant_context
from app.db.models import Conversation


async def _signup(client: httpx.AsyncClient, slug: str, email: str) -> str:
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
    return resp.json()["access_token"]


def _tenant_id(access_token: str) -> UUID:
    return UUID(decode_token(access_token)["tid"])


async def _seed_conversation(tenant_id: UUID, title: str) -> None:
    async with async_session_factory() as session:
        async with session.begin():
            await set_tenant_context(session, tenant_id)
            session.add(Conversation(tenant_id=tenant_id, title=title))


async def test_unauthenticated_request_is_401(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/v1/conversations")
    assert resp.status_code == 401


async def test_lists_only_own_tenant_conversations(client: httpx.AsyncClient) -> None:
    access_a = await _signup(client, "olivo-a", "a@olivo.test")
    await _seed_conversation(_tenant_id(access_a), "A's conversation")

    resp = await client.get(
        "/api/v1/conversations", headers={"Authorization": f"Bearer {access_a}"}
    )
    assert resp.status_code == 200
    titles = [c["title"] for c in resp.json()]
    assert titles == ["A's conversation"]


async def test_other_tenant_cannot_see_foreign_conversations(
    client: httpx.AsyncClient,
) -> None:
    access_a = await _signup(client, "olivo-a", "a@olivo.test")
    await _seed_conversation(_tenant_id(access_a), "A's conversation")
    access_b = await _signup(client, "olivo-b", "b@olivo.test")

    resp = await client.get(
        "/api/v1/conversations", headers={"Authorization": f"Bearer {access_b}"}
    )
    assert resp.status_code == 200
    assert resp.json() == []  # RLS hides tenant A's row from tenant B


async def test_expired_access_token_is_401(client: httpx.AsyncClient) -> None:
    past = datetime.now(UTC) - timedelta(minutes=5)
    expired = jwt.encode(
        {
            "sub": str(uuid4()),
            "tid": str(uuid4()),
            "typ": "access",
            "iat": int((past - timedelta(minutes=20)).timestamp()),
            "exp": int(past.timestamp()),
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    resp = await client.get(
        "/api/v1/conversations", headers={"Authorization": f"Bearer {expired}"}
    )
    assert resp.status_code == 401
