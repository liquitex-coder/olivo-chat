"""HS256 JWT encode/decode for access tokens. Secret/TTLs come from settings."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.config import settings

_ALG = "HS256"


def encode_access_token(user_id: UUID, tenant_id: UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.JWT_ACCESS_TTL)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=_ALG)


def decode_token(token: str) -> dict:
    """Decode + verify signature and expiry. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[_ALG])
