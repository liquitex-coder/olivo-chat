"""Persist a user turn, get a provider reply, persist the assistant turn — all under
the caller's RLS tenant context (the conversation was already ownership-checked)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.provider import ChatProvider
from app.db.models import Message


async def generate_reply(
    *,
    session: AsyncSession,
    conversation_id: UUID,
    tenant_id: UUID,
    user_content: str,
    provider: ChatProvider,
) -> tuple[Message, Message]:
    user_msg = Message(
        conversation_id=conversation_id,
        tenant_id=tenant_id,
        role="user",
        content=user_content,
    )
    session.add(user_msg)
    await session.flush()

    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    history = [m.content for m in result.scalars().all()]

    reply_text = await provider.reply(user_message=user_content, history=history)

    assistant_msg = Message(
        conversation_id=conversation_id,
        tenant_id=tenant_id,
        role="assistant",
        content=reply_text,
    )
    session.add(assistant_msg)
    await session.flush()

    await session.refresh(user_msg)
    await session.refresh(assistant_msg)
    return user_msg, assistant_msg
