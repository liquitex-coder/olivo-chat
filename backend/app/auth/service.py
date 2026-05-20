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

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_tokens import encode_access_token
from app.auth.password import hash_password
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
