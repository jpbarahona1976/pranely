"""Billing endpoints - plans, subscription, Stripe checkout."""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import BillingPlan, BillingPlanCode, Organization, Subscription, SubscriptionStatus
from app.api.v1.deps import get_current_user_with_org


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/billing", tags=["Billing"])


# --- Schemas ---

class BillingPlanResponse(BaseModel):
    """Schema for billing plan response."""
    id: int
    code: str
    name: str
    description: Optional[str]
    price_usd_cents: int
    doc_limit: int
    doc_limit_period: str
    features: dict = {}
    is_active: bool

    model_config = {"from_attributes": True}


class BillingPlanListResponse(BaseModel):
    """Schema for listing billing plans."""
    plans: List[BillingPlanResponse]


class SubscriptionResponse(BaseModel):
    """Schema for subscription response."""
    id: int
    plan_code: str
    plan_name: str
    status: str
    started_at: Optional[datetime] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    stripe_sub_id: Optional[str] = None

    model_config = {"from_attributes": True}


class SubscriptionDetailResponse(BaseModel):
    """Schema for detailed subscription with usage."""
    id: int
    organization_id: int
    plan_code: str
    plan_name: str
    status: str
    started_at: Optional[datetime] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    stripe_sub_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    doc_limit: int
    docs_used: int = 0

    model_config = {"from_attributes": True}


class CheckoutRequest(BaseModel):
    """Schema for Stripe checkout request."""
    success_url: str = Field(..., description="Redirect URL on success")
    cancel_url: str = Field(..., description="Redirect URL on cancel")


class CheckoutResponse(BaseModel):
    """Schema for Stripe checkout response."""
    checkout_url: str
    session_id: str
    plan_code: str


# --- Endpoints ---

@router.get(
    "/plans",
    response_model=BillingPlanListResponse,
    summary="List billing plans",
    description="List all available billing plans.",
)
async def list_plans(
    db: AsyncSession = Depends(get_db),
) -> BillingPlanListResponse:
    """
    List all active billing plans.
    
    Returns plans available for subscription.
    """
    result = await db.execute(
        select(BillingPlan)
        .where(BillingPlan.is_active == True)
        .order_by(BillingPlan.price_usd_cents)
    )
    plans = result.scalars().all()
    
    return BillingPlanListResponse(
        plans=[
            BillingPlanResponse(
                id=plan.id,
                code=plan.code.value,
                name=plan.name,
                description=plan.description,
                price_usd_cents=plan.price_usd_cents,
                doc_limit=plan.doc_limit,
                doc_limit_period=plan.doc_limit_period,
                features=plan.features_json or {},
                is_active=plan.is_active,
            )
            for plan in plans
        ]
    )


@router.get(
    "/subscription",
    response_model=SubscriptionDetailResponse,
    summary="Get current subscription",
    description="Get the current organization subscription with usage.",
)
async def get_subscription(
    db: AsyncSession = Depends(get_db),
    user_org: tuple = Depends(get_current_user_with_org),
) -> SubscriptionDetailResponse:
    """
    Get current organization subscription.
    
    Requires authentication and returns subscription details with usage.
    """
    user, org_id = user_org
    
    # Get subscription
    result = await db.execute(
        select(Subscription)
        .where(Subscription.organization_id == org_id)
    )
    subscription = result.scalar_one_or_none()
    
    if subscription is None:
        # Return empty subscription for orgs without subscription
        return SubscriptionDetailResponse(
            id=0,
            organization_id=org_id,
            plan_code="none",
            plan_name="No subscription",
            status="inactive",
            started_at=None,
            current_period_start=None,
            current_period_end=None,
            stripe_sub_id=None,
            stripe_customer_id=None,
            doc_limit=0,
            docs_used=0,
        )
    
    # Get plan details
    result = await db.execute(
        select(BillingPlan).where(BillingPlan.id == subscription.plan_id)
    )
    plan = result.scalar_one_or_none()
    
    # Get organization for stripe_customer_id
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    
    # Get current usage (from UsageCycle)
    from app.models import UsageCycle
    
    current_month = datetime.now().strftime("%Y-%m")
    result = await db.execute(
        select(UsageCycle)
        .where(
            UsageCycle.subscription_id == subscription.id,
            UsageCycle.month_year == current_month,
        )
    )
    usage = result.scalar_one_or_none()
    
    return SubscriptionDetailResponse(
        id=subscription.id,
        organization_id=org_id,
        plan_code=plan.code.value if plan else "unknown",
        plan_name=plan.name if plan else "Unknown",
        status=subscription.status.value,
        started_at=subscription.started_at,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        stripe_sub_id=subscription.stripe_sub_id,
        stripe_customer_id=subscription.stripe_customer_id or org.stripe_customer_id if org else None,
        doc_limit=plan.doc_limit if plan else 0,
        docs_used=usage.docs_used if usage else 0,
    )


@router.post(
    "/subscribe/{plan_code}",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to plan",
    description="Create Stripe checkout session for subscription.",
)
async def subscribe(
    plan_code: str,
    request: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    user_org: tuple = Depends(get_current_user_with_org),
) -> CheckoutResponse:
    """
    Create Stripe checkout session for plan subscription.
    
    Returns Stripe checkout URL for payment processing.
    Note: Stripe integration is stubbed for MVP - returns mock URL.
    """
    user, org_id = user_org
    
    # Validate plan_code
    try:
        code = BillingPlanCode(plan_code)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/billing",
                "title": "Invalid plan",
                "status": 400,
                "detail": f"Plan code '{plan_code}' is not valid",
            },
        )
    
    # Get plan
    result = await db.execute(
        select(BillingPlan).where(BillingPlan.code == code)
    )
    plan = result.scalar_one_or_none()
    
    if plan is None or not plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/billing",
                "title": "Plan not available",
                "status": 400,
                "detail": "Plan is not available for subscription",
            },
        )
    
    # Get organization
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/tenant",
                "title": "Organization not found",
                "status": 404,
                "detail": "Organization does not exist",
            },
        )
    
    # REAL: Create Stripe Checkout Session
    import stripe
    
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "https://api.pranely.com/errors/billing",
                "title": "Stripe not configured",
                "status": 500,
                "detail": "STRIPE_SECRET_KEY not configured",
            },
        )
    
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': f'Pranely {plan.name}'},
                    'unit_amount': plan.price_usd_cents,
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=settings.FRONTEND_URL + '/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=settings.FRONTEND_URL + '/billing',
            metadata={'org_id': str(org_id), 'plan_code': plan_code},
        )
        session_id = session.id
        checkout_url = session.url
    except Exception as e:
        logger.error(f"Stripe checkout session creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "type": "https://api.pranely.com/errors/billing",
                "title": "Checkout failed",
                "status": 500,
                "detail": f"Failed to create Stripe checkout session: {str(e)}",
            },
        )
    
    return CheckoutResponse(
        checkout_url=checkout_url,
        session_id=session_id,
        plan_code=plan_code,
    )


# Import webhook router and include it
from app.api.v1.billing.webhook import router as webhook_router

router.include_router(webhook_router)