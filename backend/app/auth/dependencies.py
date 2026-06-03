"""Auth dependencies: a request-scoped DB session and the Bearer authenticator.

`get_current_user` decodes the access JWT and calls `set_tenant_context()` on the
request session, arming RLS for every subsequent query in the same request.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_tokens import decode_token
from app.db import async_session_factory, set_tenant_context


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """One transaction per request; commit on success, rollback on error.

    FastAPI caches this within a request, so `get_current_user` and the route
    handler share the same session (and therefore the same tenant context).
    """
    async with async_session_factory() as session:
        async with session.begin():
            yield session


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    tenant_id: UUID


async def get_current_user(
    authorization: str = Header(default=""),
    session: AsyncSession = Depends(get_db_session),
) -> CurrentUser:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bearer token required")
    token = authorization[len("Bearer ") :]
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from e
    if payload.get("typ") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "wrong token type")
    try:
        tenant_id = UUID(payload["tid"])
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError) as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "malformed claims") from e

    await set_tenant_context(session, tenant_id)
    return CurrentUser(id=user_id, tenant_id=tenant_id)
