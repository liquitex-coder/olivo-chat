"""HS256 JWT encode/decode unit tests (Step 3 §1.4)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.auth.jwt_tokens import ACCESS_TYPE, decode_token, encode_access_token
from app.config import settings


def test_encode_then_decode_roundtrip_carries_all_claims() -> None:
    user_id = uuid4()
    tenant_id = uuid4()

    token = encode_access_token(user_id, tenant_id)
    payload = decode_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["tid"] == str(tenant_id)
    assert payload["typ"] == ACCESS_TYPE
    assert isinstance(payload["iat"], int)
    assert isinstance(payload["exp"], int)
    assert payload["exp"] - payload["iat"] == settings.JWT_ACCESS_TTL


def test_expired_token_is_rejected() -> None:
    past = datetime.now(UTC) - timedelta(seconds=settings.JWT_ACCESS_TTL + 60)
    token = encode_access_token(uuid4(), uuid4(), now=past)

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


def test_token_signed_with_wrong_secret_is_rejected() -> None:
    forged = jwt.encode(
        {"sub": str(uuid4()), "tid": str(uuid4()), "typ": ACCESS_TYPE},
        "not-the-real-secret",
        algorithm="HS256",
    )

    with pytest.raises(jwt.InvalidSignatureError):
        decode_token(forged)


def test_tampered_payload_is_rejected() -> None:
    token = encode_access_token(uuid4(), uuid4())
    head, payload, sig = token.split(".")
    tampered = f"{head}.{payload}X.{sig}"

    with pytest.raises(jwt.PyJWTError):
        decode_token(tampered)
