"""ORM integration tests for tenants, conversations, and messages."""
from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, Message, Tenant
from app.db.tenant_context import set_tenant_context


def _unique_slug(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_tenant_insert_select_update(db_session: AsyncSession) -> None:
    slug = _unique_slug("tenant")
    tenant = Tenant(name="Trattoria Olivo", slug=slug, plan="free")
    db_session.add(tenant)
    await db_session.flush()

    result = await db_session.execute(select(Tenant).where(Tenant.id == tenant.id))
    loaded = result.scalar_one()
    assert loaded.name == "Trattoria Olivo"
    assert loaded.slug == slug
    assert loaded.plan == "free"

    old_updated = loaded.updated_at
    await asyncio.sleep(0.02)
    loaded.name = "Trattoria Olivo Updated"
    await db_session.flush()
    await db_session.refresh(loaded)
    assert loaded.updated_at >= old_updated
    assert loaded.name == "Trattoria Olivo Updated"


@pytest.mark.asyncio
async def test_conversation_insert_select_update(db_session: AsyncSession) -> None:
    tenant = Tenant(name="Tenant A", slug=_unique_slug("conv-tenant"))
    db_session.add(tenant)
    await db_session.flush()

    await set_tenant_context(db_session, tenant.id)
    conv = Conversation(tenant_id=tenant.id, title="Lunch menu")
    db_session.add(conv)
    await db_session.flush()

    result = await db_session.execute(select(Conversation).where(Conversation.id == conv.id))
    loaded = result.scalar_one()
    assert loaded.tenant_id == tenant.id
    assert loaded.title == "Lunch menu"

    old_updated = loaded.updated_at
    await asyncio.sleep(0.02)
    loaded.title = "Dinner menu"
    await db_session.flush()
    await db_session.refresh(loaded)
    assert loaded.updated_at >= old_updated
    assert loaded.title == "Dinner menu"


@pytest.mark.asyncio
async def test_message_insert_select(db_session: AsyncSession) -> None:
    tenant = Tenant(name="Tenant B", slug=_unique_slug("msg-tenant"))
    db_session.add(tenant)
    await db_session.flush()

    await set_tenant_context(db_session, tenant.id)
    conv = Conversation(tenant_id=tenant.id, title="Chat")
    db_session.add(conv)
    await db_session.flush()

    msg = Message(
        conversation_id=conv.id,
        tenant_id=tenant.id,
        role="user",
        content="Hello",
    )
    db_session.add(msg)
    await db_session.flush()

    result = await db_session.execute(select(Message).where(Message.id == msg.id))
    loaded = result.scalar_one()
    assert loaded.conversation_id == conv.id
    assert loaded.tenant_id == tenant.id
    assert loaded.role == "user"
    assert loaded.content == "Hello"


@pytest.mark.asyncio
async def test_conversation_rejects_missing_tenant(db_session: AsyncSession) -> None:
    missing_tenant_id = uuid.uuid4()
    await set_tenant_context(db_session, missing_tenant_id)
    conv = Conversation(tenant_id=missing_tenant_id, title="orphan")
    db_session.add(conv)

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_tenant_delete_cascades_conversations_and_messages(
    db_session: AsyncSession,
) -> None:
    tenant = Tenant(name="Cascade Tenant", slug=_unique_slug("cascade"))
    db_session.add(tenant)
    await db_session.flush()

    await set_tenant_context(db_session, tenant.id)
    conv = Conversation(tenant_id=tenant.id, title="To delete")
    db_session.add(conv)
    await db_session.flush()

    msg = Message(
        conversation_id=conv.id,
        tenant_id=tenant.id,
        role="assistant",
        content="Bye",
    )
    db_session.add(msg)
    await db_session.flush()

    conv_id = conv.id
    msg_id = msg.id
    tenant_id = tenant.id

    await db_session.delete(tenant)
    await db_session.flush()

    conv_result = await db_session.execute(
        select(Conversation).where(Conversation.id == conv_id)
    )
    assert conv_result.scalar_one_or_none() is None

    msg_result = await db_session.execute(select(Message).where(Message.id == msg_id))
    assert msg_result.scalar_one_or_none() is None

    tenant_result = await db_session.execute(select(Tenant).where(Tenant.id == tenant_id))
    assert tenant_result.scalar_one_or_none() is None
