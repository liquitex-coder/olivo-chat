"""GET /api/v1/conversations RLS integration tests (Step 3 §8.5)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_tokens import ACCESS_TYPE
from app.config import settings
from app.db.models import Conversation
from app.db.tenant_context import set_tenant_context
from app.main import app

client = TestClient(app)


def _signup() -> dict[str, str]:
    """Return the full signup response body."""
    slug = f"pe-{uuid.uuid4().hex[:8]}"
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "tenant_name": "Acme",
            "tenant_slug": slug,
            "email": f"owner-{slug}@example.com",
            "password": "correct_horse_battery",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _tenant_id_from_access(token: str) -> uuid.UUID:
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    return uuid.UUID(payload["tid"])


@pytest.mark.asyncio
async def test_conversations_requires_authorization() -> None:
    response = client.get("/api/v1/conversations")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_conversations_returns_only_callers_tenant_rows(
    db_session: AsyncSession,
) -> None:
    tokens_a = _signup()
    tenant_a = _tenant_id_from_access(tokens_a["access_token"])

    await set_tenant_context(db_session, tenant_a)
    db_session.add(Conversation(tenant_id=tenant_a, title="A-visible"))
    await db_session.commit()

    response = client.get(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {tokens_a['access_token']}"},
    )
    assert response.status_code == 200, response.text
    titles = [row["title"] for row in response.json()]
    assert "A-visible" in titles


@pytest.mark.asyncio
async def test_other_tenants_conversations_are_invisible(
    db_session: AsyncSession,
) -> None:
    tokens_a = _signup()
    tokens_b = _signup()
    tenant_a = _tenant_id_from_access(tokens_a["access_token"])
    tenant_b = _tenant_id_from_access(tokens_b["access_token"])

    await set_tenant_context(db_session, tenant_a)
    db_session.add(Conversation(tenant_id=tenant_a, title="A-secret"))
    await db_session.commit()

    response_b = client.get(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {tokens_b['access_token']}"},
    )
    assert response_b.status_code == 200, response_b.text
    titles_b = [row["title"] for row in response_b.json()]
    assert "A-secret" not in titles_b

    # Sanity: B has nothing yet; A still sees the row via its own token.
    assert all(row["tenant_id"] == str(tenant_b) for row in response_b.json())


@pytest.mark.asyncio
async def test_expired_access_token_returns_401() -> None:
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    expired = datetime.now(UTC) - timedelta(seconds=settings.JWT_ACCESS_TTL + 60)
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "typ": ACCESS_TYPE,
        "iat": int(expired.timestamp()),
        "exp": int((expired + timedelta(seconds=settings.JWT_ACCESS_TTL)).timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")

    response = client.get(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
