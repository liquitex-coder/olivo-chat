"""Row Level Security isolation tests."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, Message, Tenant
from app.db.tenant_context import set_tenant_context


def _unique_slug(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _create_two_tenants(db_session: AsyncSession) -> tuple[Tenant, Tenant]:
    tenant_a = Tenant(name="Tenant A", slug=_unique_slug("rls-a"))
    tenant_b = Tenant(name="Tenant B", slug=_unique_slug("rls-b"))
    db_session.add_all([tenant_a, tenant_b])
    await db_session.flush()
    return tenant_a, tenant_b


@pytest.mark.asyncio
async def test_rls_isolates_conversations(db_session: AsyncSession) -> None:
    tenant_a, tenant_b = await _create_two_tenants(db_session)
    await set_tenant_context(db_session, tenant_a.id)
    conv = Conversation(tenant_id=tenant_a.id, title="A の会話")
    db_session.add(conv)
    await db_session.flush()

    await set_tenant_context(db_session, tenant_b.id)
    result = await db_session.execute(select(Conversation))
    assert result.scalars().all() == []

    await set_tenant_context(db_session, tenant_a.id)
    result = await db_session.execute(select(Conversation))
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_rls_isolates_messages(db_session: AsyncSession) -> None:
    tenant_a, tenant_b = await _create_two_tenants(db_session)
    await set_tenant_context(db_session, tenant_a.id)
    conv = Conversation(tenant_id=tenant_a.id, title="A")
    db_session.add(conv)
    await db_session.flush()

    msg = Message(
        conversation_id=conv.id,
        tenant_id=tenant_a.id,
        role="user",
        content="secret",
    )
    db_session.add(msg)
    await db_session.flush()

    await set_tenant_context(db_session, tenant_b.id)
    result = await db_session.execute(select(Message))
    assert result.scalars().all() == []

    await set_tenant_context(db_session, tenant_a.id)
    result = await db_session.execute(select(Message))
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_rls_without_tenant_context_returns_empty(db_session: AsyncSession) -> None:
    tenant = Tenant(name="Tenant X", slug=_unique_slug("rls-none"))
    db_session.add(tenant)
    await db_session.flush()

    await set_tenant_context(db_session, tenant.id)
    conv = Conversation(tenant_id=tenant.id, title="hidden")
    db_session.add(conv)
    await db_session.flush()

    await db_session.execute(text("RESET app.current_tenant_id"))

    conv_result = await db_session.execute(select(Conversation))
    assert conv_result.scalars().all() == []

    msg_result = await db_session.execute(select(Message))
    assert msg_result.scalars().all() == []
