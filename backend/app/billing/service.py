"""Billing service: plan ranking + applying a (verified) subscription event."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Tenant

PLAN_RANK = {"free": 0, "pro": 1, "business": 2}
_RELEVANT_EVENTS = {"checkout.session.completed", "customer.subscription.updated"}


def has_at_least(plan: str, required: str) -> bool:
    """True if `plan` is at least `required` in the free < pro < business order."""
    return PLAN_RANK.get(plan, 0) >= PLAN_RANK.get(required, 0)


async def apply_subscription_event(*, session: AsyncSession, event: dict) -> bool:
    """Set the tenant's plan from a subscription event. Returns True if applied.

    `tenants` has no RLS (it predates the tenant context), so the webhook — which is
    authenticated by signature, not by a JWT — can update the plan by id.
    """
    if event.get("type") not in _RELEVANT_EVENTS:
        return False
    obj = event.get("data", {}).get("object", {})
    metadata = obj.get("metadata", {}) if isinstance(obj, dict) else {}
    raw_tenant_id = metadata.get("tenant_id")
    plan = metadata.get("plan")
    if not raw_tenant_id or plan not in PLAN_RANK:
        return False
    try:
        tenant_id = UUID(str(raw_tenant_id))
    except ValueError:
        return False

    result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        return False
    tenant.plan = plan
    await session.flush()
    return True
