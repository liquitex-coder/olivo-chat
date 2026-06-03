"""Auth business logic: signup, login, refresh rotation, logout.

Service functions raise AuthError for expected auth failures; the router maps
that to an HTTP status. The generic "Invalid credentials" message never reveals
whether the email exists.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_tokens import encode_access_token
from app.auth.password import hash_password, verify_password
from app.config import settings
from app.db import set_tenant_context
from app.db.models import RefreshToken, Tenant, User


class AuthError(Exception):
    """Expected authentication failure, mapped to an HTTP status by the router."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _hash_refresh(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _new_refresh_raw(tenant_id: UUID) -> str:
    """Opaque token prefixed with the (non-secret) tenant id.

    The refresh endpoint is pre-auth: it must locate the row before the tenant is
    known. Because `refresh_tokens` is RLS-FORCEd and the app role is NOBYPASSRLS,
    a lookup with no tenant context returns nothing. Carrying the tenant id in the
    token lets `rotate` set the RLS context *before* the by-hash query, so the
    strict tenant `USING` policy is preserved (security still rests on the
    unguessable random part + the stored hash, never on the prefix).
    """
    return f"{tenant_id}.{secrets.token_urlsafe(48)}"


def _tenant_from_raw(raw: str) -> UUID:
    return UUID(raw.split(".", 1)[0])


async def _issue_refresh(
    session: AsyncSession, *, tenant_id: UUID, user_id: UUID
) -> str:
    """Create one refresh-token row (RLS-scoped) and return the raw token."""
    raw = _new_refresh_raw(tenant_id)
    row = RefreshToken(
        tenant_id=tenant_id,
        user_id=user_id,
        token_hash=_hash_refresh(raw),
        expires_at=datetime.now(UTC)
        + timedelta(seconds=settings.JWT_REFRESH_TTL),
    )
    session.add(row)
    await session.flush()
    return raw


async def signup_user(
    *,
    session: AsyncSession,
    tenant_name: str,
    tenant_slug: str,
    email: str,
    password: str,
) -> tuple[str, str]:
    """Create a new tenant + its first user; return (access_token, raw_refresh)."""
    pw_hash = hash_password(password)

    tenant = Tenant(name=tenant_name, slug=tenant_slug)
    session.add(tenant)
    await session.flush()

    user = User(tenant_id=tenant.id, email=email.lower(), password_hash=pw_hash)
    session.add(user)
    await session.flush()

    await set_tenant_context(session, tenant.id)  # refresh_tokens is RLS-enabled
    raw_refresh = await _issue_refresh(session, tenant_id=tenant.id, user_id=user.id)
    access = encode_access_token(user.id, tenant.id)
    return access, raw_refresh


async def authenticate_user(
    *, session: AsyncSession, email: str, password: str
) -> tuple[str, str]:
    """Verify credentials; return (access_token, raw_refresh). Raises AuthError(401)."""
    result = await session.execute(
        select(User).where(User.email == email.lower()).limit(1)
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
        raise AuthError(401, "Invalid credentials")

    await set_tenant_context(session, user.tenant_id)
    raw_refresh = await _issue_refresh(
        session, tenant_id=user.tenant_id, user_id=user.id
    )
    access = encode_access_token(user.id, user.tenant_id)
    return access, raw_refresh


async def rotate_refresh_token(
    *, session: AsyncSession, raw_refresh: str
) -> tuple[str, str]:
    """Rotate a refresh token: revoke the old, issue new. Raises AuthError(401)."""
    try:
        tenant_id = _tenant_from_raw(raw_refresh)
    except (ValueError, IndexError) as e:
        raise AuthError(401, "Invalid refresh token") from e

    # Arm RLS with the token's tenant before the by-hash lookup (see _new_refresh_raw).
    await set_tenant_context(session, tenant_id)

    token_hash = _hash_refresh(raw_refresh)
    now = datetime.now(UTC)
    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise AuthError(401, "Invalid refresh token")

    row.revoked_at = now
    await session.flush()

    raw_new = await _issue_refresh(session, tenant_id=row.tenant_id, user_id=row.user_id)
    access = encode_access_token(row.user_id, row.tenant_id)
    return access, raw_new


async def revoke_refresh_token(
    *, session: AsyncSession, user_id: UUID, raw_refresh: str
) -> None:
    """Revoke the presented refresh token for the current user (idempotent)."""
    token_hash = _hash_refresh(raw_refresh)
    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        row.revoked_at = datetime.now(UTC)
        await session.flush()
