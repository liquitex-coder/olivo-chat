"""HS256 JWT encode / decode (Step 3 §1.4).

Claims for access tokens:
- sub: user_id (UUID string)
- tid: tenant_id (UUID string)
- typ: "access"
- iat / exp: unix seconds

Refresh tokens are NOT JWTs; see app/auth/service.py for the
`secrets.token_urlsafe(48)` + SHA-256-in-DB scheme.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt

from app.config import settings

ALGORITHM = "HS256"
ACCESS_TYPE = "access"


def encode_access_token(
    user_id: UUID,
    tenant_id: UUID,
    *,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(seconds=settings.JWT_ACCESS_TTL)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "typ": ACCESS_TYPE,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode + validate signature, exp, iat. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
