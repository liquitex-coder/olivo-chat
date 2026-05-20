"""FastAPI dependencies for the auth layer (Step 3 §3.5 + §6.3).

`get_current_user` is the single entry point routes use to require an
authenticated request. It decodes the bearer JWT, validates its type
and claims, and arms `app.current_tenant_id` for downstream RLS-aware
queries on the same session.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_tokens import ACCESS_TYPE, decode_token
from app.db.session import async_session_factory
from app.db.tenant_context import set_tenant_context


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield a transactional async session; commit on clean exit."""
    async with async_session_factory() as session:
        async with session.begin():
            yield session


SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    tenant_id: UUID


_BEARER_PREFIX = "Bearer "


async def get_current_user(
    session: SessionDep,
    authorization: Annotated[str, Header()] = "",
) -> CurrentUser:
    if not authorization.startswith(_BEARER_PREFIX):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Bearer token required"
        )

    token = authorization[len(_BEARER_PREFIX):]
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token"
        ) from exc

    if payload.get("typ") != ACCESS_TYPE:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="wrong token type"
        )

    try:
        tenant_id = UUID(payload["tid"])
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="malformed token claims"
        ) from exc

    await set_tenant_context(session, tenant_id)
    return CurrentUser(id=user_id, tenant_id=tenant_id)
