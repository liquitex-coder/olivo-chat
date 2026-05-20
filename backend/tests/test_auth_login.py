"""POST /api/v1/auth/login integration tests (Step 3 §8.2)."""
from __future__ import annotations

import uuid

import jwt
from fastapi.testclient import TestClient

from app.auth.jwt_tokens import ACCESS_TYPE
from app.config import settings
from app.main import app

client = TestClient(app)


def _signup_user(password: str = "correct_horse_battery") -> tuple[str, str]:
    """Create a fresh tenant + user; return (email, password)."""
    slug = f"lg-{uuid.uuid4().hex[:8]}"
    email = f"owner-{slug}@example.com"
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "tenant_name": "Acme",
            "tenant_slug": slug,
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 201, response.text
    return email, password


def test_login_with_correct_password_returns_tokens() -> None:
    email, password = _signup_user()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_with_wrong_password_returns_401() -> None:
    email, _ = _signup_user()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "definitely_wrong_pw"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_with_unknown_email_returns_401() -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"no-such-{uuid.uuid4().hex[:8]}@example.com",
            "password": "correct_horse_battery",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_access_token_claims_are_well_formed() -> None:
    email, password = _signup_user()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text

    token = response.json()["access_token"]
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])

    assert payload["typ"] == ACCESS_TYPE
    assert "sub" in payload and uuid.UUID(payload["sub"])
    assert "tid" in payload and uuid.UUID(payload["tid"])
    assert isinstance(payload["iat"], int)
    assert isinstance(payload["exp"], int)
    assert payload["exp"] - payload["iat"] == settings.JWT_ACCESS_TTL
