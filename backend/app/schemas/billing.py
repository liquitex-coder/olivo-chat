"""Billing Pydantic schemas."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    plan: Literal["pro", "business"]


class CheckoutResponse(BaseModel):
    checkout_url: str


class PlanResponse(BaseModel):
    plan: Literal["free", "pro", "business"]
