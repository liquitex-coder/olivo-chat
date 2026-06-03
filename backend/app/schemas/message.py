"""Message Pydantic schemas."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageBase(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class MessageCreate(MessageBase):
    pass


class ChatRequest(BaseModel):
    """A customer chat turn — content only; role is always 'user'."""

    content: str = Field(min_length=1, max_length=4000)


class MessageRead(MessageBase):
    id: UUID
    conversation_id: UUID
    tenant_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
