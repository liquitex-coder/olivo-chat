"""Billing endpoints: checkout, plan, webhook, and a plan-gated demo feature.

The webhook is unauthenticated by JWT on purpose — the caller is the billing
provider, authenticated by the signature over the raw body. `tenants` has no RLS,
so the plan update needs no tenant context.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, get_current_user, get_db_session
from app.billing.provider import (
    BillingProvider,
    WebhookVerificationError,
    get_billing_provider,
)
from app.billing.service import apply_subscription_event, has_at_least
from app.db.models import Tenant
from app.schemas.billing import CheckoutRequest, CheckoutResponse, PlanResponse

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


async def _current_plan(session: AsyncSession, tenant_id: UUID) -> str:
    result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    return tenant.plan if tenant is not None else "free"


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(
    payload: CheckoutRequest,
    current_user: CurrentUser = Depends(get_current_user),
    provider: BillingProvider = Depends(get_billing_provider),
) -> CheckoutResponse:
    url = provider.create_checkout_session(
        tenant_id=str(current_user.tenant_id), plan=payload.plan
    )
    return CheckoutResponse(checkout_url=url)


@router.get("/plan", response_model=PlanResponse)
async def get_plan(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PlanResponse:
    return PlanResponse(plan=await _current_plan(session, current_user.tenant_id))


@router.post("/webhook")
async def webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    provider: BillingProvider = Depends(get_billing_provider),
) -> dict:
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    try:
        event = provider.verify_webhook(payload=payload, signature=signature)
    except WebhookVerificationError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid signature") from e
    updated = await apply_subscription_event(session=session, event=event)
    return {"received": True, "updated": updated}


@router.get("/premium")
async def premium_feature(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Demo entitlement gated on a paid plan (pro or business)."""
    plan = await _current_plan(session, current_user.tenant_id)
    if not has_at_least(plan, "pro"):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED, "upgrade to a paid plan"
        )
    return {"feature": "premium analytics", "plan": plan}
