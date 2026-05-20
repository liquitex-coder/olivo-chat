"""Auth business logic (Step 3 §3).

All public functions take an AsyncSession; the caller controls
transaction scope. Tenant context is set via `set_tenant_context()`
before any RLS-protected write so the `refresh_tokens` INSERT lands
in the right row-level partition.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_tokens import encode_access_token
from app.auth.password import hash_password, verify_password
from app.config import settings
from app.db.models import RefreshToken, Tenant, User
from app.db.tenant_context import set_tenant_context


@dataclass(frozen=True)
class IssuedTokens:
    """Pair of credentials returned to the client after auth state changes."""

    access_token: str
    refresh_token: str  # raw value -- only on the wire, never re-derivable from DB


class InvalidCredentialsError(Exception):
    """Raised by authenticate_user / rotate / revoke when a credential is wrong."""


def _hash_refresh(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _new_refresh_raw() -> str:
    return secrets.token_urlsafe(48)


def _refresh_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(seconds=settings.JWT_REFRESH_TTL)


async def _issue_refresh(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
) -> str:
    raw = _new_refresh_raw()
    session.add(
        RefreshToken(
            tenant_id=tenant_id,
            user_id=user_id,
            token_hash=_hash_refresh(raw),
            expires_at=_refresh_expiry(),
        )
    )
    await session.flush()
    return raw


async def signup_user(
    *,
    session: AsyncSession,
    tenant_name: str,
    tenant_slug: str,
    email: str,
    password: str,
) -> tuple[Tenant, User, IssuedTokens]:
    """Create a new tenant + first user and return both rows + tokens.

    Email is lowercased here as a defence-in-depth measure in addition to
    the schema validator -- service callers (not just routers) get the
    normalisation for free.
    """
    pw_hash = hash_password(password)

    tenant = Tenant(name=tenant_name, slug=tenant_slug)
    session.add(tenant)
    await session.flush()

    user = User(
        tenant_id=tenant.id,
        email=email.lower(),
        password_hash=pw_hash,
    )
    session.add(user)
    await session.flush()

    # refresh_tokens is RLS-enabled; arm the GUC before INSERT
    await set_tenant_context(session, tenant.id)

    raw_refresh = await _issue_refresh(session, tenant_id=tenant.id, user_id=user.id)
    access = encode_access_token(user.id, tenant.id)
    return tenant, user, IssuedTokens(access_token=access, refresh_token=raw_refresh)


async def authenticate_user(
    *,
    session: AsyncSession,
    email: str,
    password: str,
) -> tuple[User, IssuedTokens]:
    """Verify credentials and return the user + freshly issued tokens.

    Per Step 3 TaskBrief §3.2, the response is identical (401 "Invalid
    credentials") for both unknown email and wrong password to avoid
    user-enumeration leaks. MVP does not yet defend against timing-side
    channels.

    For the MVP scope (§1.2: 1 user = 1 tenant), `lower(email)` is
    treated as effectively unique across the platform. If multiple
    matches are ever returned (multi-tenant overlap), we accept the
    first row.
    """
    row = (
        await session.execute(
            select(User).where(User.email == email.lower()).limit(1)
        )
    ).scalar_one_or_none()

    if row is None or not verify_password(password, row.password_hash):
        raise InvalidCredentialsError("invalid email or password")

    await set_tenant_context(session, row.tenant_id)
    raw_refresh = await _issue_refresh(session, tenant_id=row.tenant_id, user_id=row.id)
    access = encode_access_token(row.id, row.tenant_id)
    return row, IssuedTokens(access_token=access, refresh_token=raw_refresh)


async def rotate_refresh_token(
    *,
    session: AsyncSession,
    raw_refresh_token: str,
) -> IssuedTokens:
    """Rotate the supplied refresh token (§3.3).

    A raw token is accepted only if its SHA-256 hash matches an
    un-revoked, un-expired row. The matched row is then revoked and a
    new (access, refresh) pair is issued. Tenant context is set from
    the matched row before any writes so the RLS-protected INSERT
    lands in the right partition.
    """
    token_hash = _hash_refresh(raw_refresh_token)
    now = datetime.now(UTC)

    row = (
        await session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
        )
    ).scalar_one_or_none()

    if row is None:
        raise InvalidCredentialsError("refresh token is invalid or expired")

    await set_tenant_context(session, row.tenant_id)

    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.id == row.id)
        .values(revoked_at=now)
    )

    new_raw = await _issue_refresh(
        session, tenant_id=row.tenant_id, user_id=row.user_id
    )
    new_access = encode_access_token(row.user_id, row.tenant_id)
    return IssuedTokens(access_token=new_access, refresh_token=new_raw)


async def revoke_refresh_token(
    *,
    session: AsyncSession,
    raw_refresh_token: str,
    user_id: UUID,
) -> None:
    """Revoke the supplied refresh token if it belongs to `user_id` (§3.4).

    Caller (the /logout route) has already authenticated the bearer
    token and primed `set_tenant_context`; here we just write the
    revocation. A no-op (token already revoked, expired, or unknown)
    is treated as success so logout is idempotent.
    """
    await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == _hash_refresh(raw_refresh_token),
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
