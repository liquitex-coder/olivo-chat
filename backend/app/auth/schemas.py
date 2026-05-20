"""Auth request / response Pydantic schemas (Step 3 §4)."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.auth.password import MAX_PASSWORD_LEN, MIN_PASSWORD_LEN


class _EmailNormalizingModel(BaseModel):
    """Mixin that lowercases the `email` field on input (§1.3)."""

    @field_validator("email", mode="before", check_fields=False)
    @classmethod
    def _lowercase_email(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lower()
        return v


class SignupRequest(_EmailNormalizingModel):
    tenant_name: str = Field(min_length=1, max_length=255)
    tenant_slug: str = Field(min_length=1, max_length=64)
    email: EmailStr
    password: str = Field(min_length=MIN_PASSWORD_LEN, max_length=MAX_PASSWORD_LEN)


class LoginRequest(_EmailNormalizingModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LEN)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 — OAuth2 scheme name, not a credential


class UserRead(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str

    model_config = ConfigDict(from_attributes=True)
