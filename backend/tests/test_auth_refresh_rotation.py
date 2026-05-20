"""POST /api/v1/auth/refresh rotation tests (Step 3 §8.3)."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _signup_and_get_refresh() -> str:
    slug = f"rf-{uuid.uuid4().hex[:8]}"
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
    return response.json()["refresh_token"]


def test_refresh_returns_new_token_pair() -> None:
    original_refresh = _signup_and_get_refresh()

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["refresh_token"] != original_refresh


def test_old_refresh_is_revoked_after_rotation() -> None:
    original_refresh = _signup_and_get_refresh()

    rotated = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert rotated.status_code == 200, rotated.text

    replay = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert replay.status_code == 401


def test_unknown_refresh_token_returns_401() -> None:
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": f"not-a-real-token-{uuid.uuid4().hex}"},
    )

    assert response.status_code == 401
