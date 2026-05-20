"""FastAPI router for /api/v1/auth (Step 3 §6.5)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import CurrentUser, SessionDep, get_current_user
from app.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
)
from app.auth.service import (
    InvalidCredentialsError,
    authenticate_user,
    revoke_refresh_token,
    rotate_refresh_token,
    signup_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenResponse,
)
async def signup(
    req: SignupRequest,
    session: SessionDep,
) -> TokenResponse:
    try:
        _, _, tokens = await signup_user(
            session=session,
            tenant_name=req.tenant_name,
            tenant_slug=req.tenant_slug,
            email=req.email,
            password=req.password,
        )
    except IntegrityError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="tenant slug or email already exists",
        ) from exc
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    session: SessionDep,
) -> TokenResponse:
    try:
        _, tokens = await authenticate_user(
            session=session, email=req.email, password=req.password
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        ) from exc
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    req: RefreshRequest,
    session: SessionDep,
) -> TokenResponse:
    try:
        tokens = await rotate_refresh_token(
            session=session, raw_refresh_token=req.refresh_token
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        ) from exc
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    req: LogoutRequest,
    session: SessionDep,
    current: Annotated[CurrentUser, Depends(get_current_user)],
) -> None:
    await revoke_refresh_token(
        session=session,
        raw_refresh_token=req.refresh_token,
        user_id=current.id,
    )
