"""Auth endpoints: signup, login, refresh (rotation), logout."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, get_db_session
from app.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
)
from app.auth.service import (
    AuthError,
    authenticate_user,
    revoke_refresh_token,
    rotate_refresh_token,
    signup_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=TokenResponse)
async def signup(
    req: SignupRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    try:
        access, refresh = await signup_user(
            session=session,
            tenant_name=req.tenant_name,
            tenant_slug=req.tenant_slug,
            email=req.email,
            password=req.password,
        )
    except IntegrityError as e:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "tenant slug or email already exists"
        ) from e
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    try:
        access, refresh = await authenticate_user(
            session=session, email=req.email, password=req.password
        )
    except AuthError as e:
        raise HTTPException(e.status_code, e.detail) from e
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    req: RefreshRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    try:
        access, new_refresh = await rotate_refresh_token(
            session=session, raw_refresh=req.refresh_token
        )
    except AuthError as e:
        raise HTTPException(e.status_code, e.detail) from e
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    req: LogoutRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    await revoke_refresh_token(
        session=session, user_id=current_user.id, raw_refresh=req.refresh_token
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
