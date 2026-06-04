"""Billing behind a provider interface. Default is offline/zero-cost; live Stripe
is gated on explicit cost approval."""
from app.billing.provider import (
    BillingProvider,
    DemoBillingProvider,
    StripeBillingProvider,
    WebhookVerificationError,
    get_billing_provider,
    sign_payload,
)
from app.billing.service import apply_subscription_event, has_at_least

__all__ = [
    "BillingProvider",
    "DemoBillingProvider",
    "StripeBillingProvider",
    "WebhookVerificationError",
    "apply_subscription_event",
    "get_billing_provider",
    "has_at_least",
    "sign_payload",
]
