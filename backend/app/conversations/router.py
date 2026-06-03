"""Minimal protected endpoint: list the current tenant's conversations.

The query has no explicit tenant filter — RLS, armed by `get_current_user`'s
`set_tenant_context()`, scopes the rows to the caller's tenant automatically.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, get_db_session
from app.db.models import Conversation
from app.schemas.conversation import ConversationRead

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationRead])
async def list_conversations(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[Conversation]:
    result = await session.execute(
        select(Conversation).order_by(Conversation.created_at.desc())
    )
    return list(result.scalars().all())
