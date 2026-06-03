"""Protected conversation + message API (FR-D1).

No query carries an explicit tenant filter — RLS, armed by `get_current_user`'s
`set_tenant_context()`, scopes every row to the caller's tenant automatically.
A conversation that belongs to another tenant is invisible here, so referencing
it returns 404 (never a cross-tenant read or write).
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, get_db_session
from app.chat import ChatProvider, generate_reply, get_chat_provider
from app.db.models import Conversation, Message
from app.schemas.conversation import ConversationCreate, ConversationRead
from app.schemas.message import ChatRequest, MessageCreate, MessageRead

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


async def _owned_conversation(
    session: AsyncSession, conversation_id: UUID
) -> Conversation:
    """Fetch a conversation visible to the current tenant or raise 404.

    RLS hides other tenants' rows, so 'not visible' and 'does not exist' collapse
    to the same 404 — no cross-tenant existence leak.
    """
    result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation not found")
    return conversation


@router.get("", response_model=list[ConversationRead])
async def list_conversations(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[Conversation]:
    result = await session.execute(
        select(Conversation).order_by(Conversation.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ConversationRead)
async def create_conversation(
    payload: ConversationCreate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Conversation:
    conversation = Conversation(tenant_id=current_user.tenant_id, title=payload.title)
    session.add(conversation)
    await session.flush()
    await session.refresh(conversation)
    return conversation


@router.get("/{conversation_id}/messages", response_model=list[MessageRead])
async def list_messages(
    conversation_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[Message]:
    await _owned_conversation(session, conversation_id)
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())


@router.post(
    "/{conversation_id}/messages",
    status_code=status.HTTP_201_CREATED,
    response_model=MessageRead,
)
async def create_message(
    conversation_id: UUID,
    payload: MessageCreate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Message:
    await _owned_conversation(session, conversation_id)
    message = Message(
        conversation_id=conversation_id,
        tenant_id=current_user.tenant_id,
        role=payload.role,
        content=payload.content,
    )
    session.add(message)
    await session.flush()
    await session.refresh(message)
    return message


@router.post(
    "/{conversation_id}/chat",
    status_code=status.HTTP_201_CREATED,
    response_model=list[MessageRead],
)
async def chat(
    conversation_id: UUID,
    payload: ChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    provider: ChatProvider = Depends(get_chat_provider),
) -> list[Message]:
    """Post a customer turn and get the assistant reply. Persists both messages
    under RLS. The provider is the demo (zero-cost) default unless a cost-approved
    Anthropic provider is swapped in."""
    await _owned_conversation(session, conversation_id)
    user_msg, assistant_msg = await generate_reply(
        session=session,
        conversation_id=conversation_id,
        tenant_id=current_user.tenant_id,
        user_content=payload.content,
        provider=provider,
    )
    return [user_msg, assistant_msg]
