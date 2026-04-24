"""Billing API schemas v1 - centralized for Fase 5A."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class BillingPlanCode(str):
    """Billing plan code enum."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str):
    """Subscription status enum."""
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"


class BillingPlanOut(BaseModel):
    """Billing plan response schema."""
    id: int = Field(description="Plan ID")
    code: str = Field(description="Plan code (free/pro/enterprise)")
    name: str = Field(description="Plan name")
    description: Optional[str] = Field(default=None, description="Plan description")
    price_usd_cents: int = Field(description="Price in USD cents (0 for free)")
    doc_limit: int = Field(description="Monthly document limit")
    doc_limit_period: str = Field(default="monthly", description="Limit period (monthly/yearly)")
    features_json: Optional[str] = Field(default=None, description="JSON features list")
    is_active: bool = Field(default=True, description="Active status")
    created_at: datetime = Field(description="Creation timestamp")

    model_config = {"from_attributes": True}


class SubscriptionOut(BaseModel):
    """Subscription response schema."""
    id: int = Field(description="Subscription ID")
    organization_id: int = Field(description="Organization ID")
    plan_id: int = Field(description="Plan ID")
    plan_code: str = Field(description="Plan code")
    stripe_subscription_id: Optional[str] = Field(default=None, description="Stripe subscription ID")
    stripe_customer_id: Optional[str] = Field(default=None, description="Stripe customer ID")
    status: str = Field(description="Status (active/paused/cancelled/past_due)")
    started_at: datetime = Field(description="Subscription start date")
    current_period_start: datetime = Field(description="Current period start")
    current_period_end: datetime = Field(description="Current period end")
    cancelled_at: Optional[datetime] = Field(default=None, description="Cancellation date")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update")

    model_config = {"from_attributes": True}


class UsageCycleOut(BaseModel):
    """Usage cycle response schema."""
    id: int = Field(description="Usage cycle ID")
    subscription_id: int = Field(description="Subscription ID")
    month_year: str = Field(description="Month/Year (YYYY-MM)")
    docs_used: int = Field(default=0, description="Documents used")
    docs_limit: int = Field(description="Documents limit")
    is_locked: bool = Field(default=False, description="Cycle locked for billing")
    overage_docs: int = Field(default=0, description="Overage documents")
    overage_charged_cents: int = Field(default=0, description="Overage charged in cents")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update")

    model_config = {"from_attributes": True}


class CheckoutSessionOut(BaseModel):
    """Stripe checkout session response."""
    checkout_url: str = Field(description="Stripe checkout URL")
    session_id: str = Field(description="Stripe session ID")
    plan_code: str = Field(description="Plan code")
    amount_cents: int = Field(description="Amount in cents")
    currency: str = Field(default="usd", description="Currency")

    model_config = {"from_attributes": True}


class SubscriptionListOut(BaseModel):
    """Subscription list response."""
    items: List[SubscriptionOut] = Field(description="List of subscriptions")
    total: int = Field(description="Total number of subscriptions")


class UsageCycleListOut(BaseModel):
    """Usage cycle list response."""
    items: List[UsageCycleOut] = Field(description="List of usage cycles")
    total: int = Field(description="Total number of cycles")
