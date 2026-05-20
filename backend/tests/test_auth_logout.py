"""POST /api/v1/auth/logout integration tests (Step 3 §8.4)."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _signup() -> tuple[str, str]:
    """Return (access_token, refresh_token)."""
    slug = f"lo-{uuid.uuid4().hex[:8]}"
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "tenant_name": "Acme",
            "tenant_slug": slug,
            "email": f"owner-{slug}@example.com",
            "password": "correct_horse_battery",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["access_token"], body["refresh_token"]


def test_logout_revokes_refresh_token() -> None:
    access, refresh = _signup()

    response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh},
        headers={"Authorization": f"Bearer {access}"},
    )

    assert response.status_code == 204


def test_logout_then_refresh_returns_401() -> None:
    access, refresh = _signup()

    logout = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert logout.status_code == 204

    replay = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert replay.status_code == 401
