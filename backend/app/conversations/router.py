"""Step 3 §6: minimal protected endpoint that proves RLS is armed by auth.

Full conversations CRUD ships in a later step. This file exists so the
auth integration tests can show that `GET /api/v1/conversations`
returns only the calling tenant's rows -- which is the whole point of
wiring `set_tenant_context()` into `get_current_user`.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.auth.dependencies import CurrentUser, SessionDep, get_current_user
from app.db.models import Conversation
from app.schemas.conversation import ConversationRead

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationRead])
async def list_conversations(
    session: SessionDep,
    _current: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[Conversation]:
    """Return conversations visible to the current tenant.

    The WHERE clause is implicit: `get_current_user` has already armed
    `app.current_tenant_id` on the request's session, and the RLS
    policy on `conversations` filters every SELECT by tenant.
    """
    result = await session.execute(
        select(Conversation).order_by(Conversation.created_at.desc())
    )
    return list(result.scalars().all())
