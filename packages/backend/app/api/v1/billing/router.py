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
from app.models import (
    BillingPlan,
    BillingPlanCode,
    Membership,
    Organization,
    Subscription,
    SubscriptionStatus,
    UserRole,
)
from app.api.v1.deps import get_current_user_with_org


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/billing", tags=["Billing"])


# =============================================================================
# RBAC: Only Owner can initiate checkout/payment
# FASE 8C.2 FIX: Hardened with double-check and tenant validation
# =============================================================================
async def require_owner_role(user_org: tuple) -> tuple:
    """
    Validate that the current user has Owner role.
    Raises 403 if not Owner.
    
    RBAC rule:
    - Owner: full pay access ✓
    - Admin: view limited (NO mutation) ✗
    - Member: cannot mutate billing ✗
    - Viewer: cannot mutate ✗
    
    FASE 8C.2 FIX: Added tenant validation to prevent bypass attempts.
    """
    user, org_id = user_org
    
    # FASE 8C.2 FIX: Validate org_id is not None or suspicious
    if org_id is None or org_id <= 0:
        logger.warning(
            f"Suspicious billing access attempt: user_id={user.id}, "
            f"org_id={org_id}, action='require_owner_role'"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/authz",
                "title": "Invalid tenant context",
                "status": 403,
                "detail": "Invalid organization context",
            },
        )
    
    async with get_db() as db:
        # Double-check: verify membership exists and role matches token
        result = await db.execute(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.organization_id == org_id,
            )
        )
        membership = result.scalar_one_or_none()
        
        if membership is None:
            logger.warning(
                f"Bypass attempt detected: user_id={user.id}, "
                f"org_id={org_id}, role_missing=True"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "type": "https://api.pranely.com/errors/authz",
                    "title": "Forbidden",
                    "status": 403,
                    "detail": "User is not a member of this organization",
                },
            )
        
        if membership.role != UserRole.OWNER:
            logger.warning(
                f"RBAC violation: user_id={user.id}, org_id={org_id}, "
                f"role={membership.role.value}, action='billing.mutation'"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "type": "https://api.pranely.com/errors/billing",
                    "title": "Forbidden",
                    "status": 403,
                    "detail": "Only organization Owner can manage billing",
                },
            )
    
    return user_org  # Return the same tuple if validation passes


# =============================================================================
# Schemas
# =============================================================================

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
    is_locked: bool = False

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


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "/plans",
    response_model=BillingPlanListResponse,
    summary="List billing plans",
    description="List all available billing plans. Public endpoint.",
)
async def list_plans(
    db: AsyncSession = Depends(get_db),
) -> BillingPlanListResponse:
    """
    List all active billing plans.
    
    Returns plans available for subscription.
    No authentication required (public endpoint).
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
    Get current organization subscription with usage details.
    
    Requires authentication.
    Multi-tenant: Returns only the org's own subscription.
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
            is_locked=False,
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
    
    current_month = datetime.utcnow().strftime("%Y-%m")
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
        is_locked=usage.is_locked if usage else False,
    )


@router.post(
    "/subscribe/{plan_code}",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to plan",
    description="Create Stripe checkout session for subscription. Owner only.",
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
    RBAC: Only Owner can initiate checkout.
    
    Audit: Registers billing.checkout.start action.
    """
    # Validate Owner role
    user, org_id = user_org
    await require_owner_role(user_org)
    
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
    
    # Log audit event (async, non-blocking)
    from app.core.audit import log_audit_event
    log_audit_event(
        organization_id=org_id,
        user_id=user.id,
        action="billing.checkout.start",
        resource_type="subscription",
        resource_id=plan_code,
        result="success",
        payload={"plan_code": plan_code, "plan_name": plan.name},
    )
    
    # Check if Stripe is configured
    if not settings.STRIPE_SECRET_KEY:
        logger.warning(f"Stripe not configured, returning mock checkout for org={org_id}")
        
        # In dev without Stripe, return a mock response
        # This allows testing the flow without real Stripe credentials
        return CheckoutResponse(
            checkout_url=f"{settings.FRONTEND_URL}/billing?mock=checkout&plan={plan_code}",
            session_id=f"mock_session_{org_id}_{plan_code}",
            plan_code=plan_code,
        )
    
    # REAL: Create Stripe Checkout Session
    import stripe
    
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    try:
        # Prepare metadata for webhook reconciliation
        metadata = {
            "org_id": str(org_id),
            "plan_code": plan_code,
            "initiated_by_user_id": str(user.id),
        }
        
        # Create or get Stripe customer
        if org.stripe_customer_id:
            customer_id = org.stripe_customer_id
        else:
            # Create new customer
            customer = stripe.Customer.create(
                email=user.email,
                metadata={"org_id": str(org_id), "org_name": org.name},
            )
            customer_id = customer.id
            org.stripe_customer_id = customer_id
        
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
            success_url=request.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.cancel_url,
            customer=customer_id,
            metadata=metadata,
        )
        
        session_id = session.id
        checkout_url = session.url
        
        logger.info(
            f"Stripe checkout created: org={org_id}, plan={plan_code}, "
            f"session_id={session_id}"
        )
        
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


@router.get(
    "/usage",
    summary="Get usage for current month",
    description="Get document usage for the current billing cycle.",
)
async def get_usage(
    db: AsyncSession = Depends(get_db),
    user_org: tuple = Depends(get_current_user_with_org),
) -> dict:
    """
    Get document usage for current billing cycle.
    
    Returns usage details including docs_used, docs_limit, and lock status.
    """
    user, org_id = user_org
    
    # Get subscription
    result = await db.execute(
        select(Subscription)
        .where(Subscription.organization_id == org_id)
    )
    subscription = result.scalar_one_or_none()
    
    if subscription is None:
        # Free tier - return default limits
        return {
            "month_year": datetime.utcnow().strftime("%Y-%m"),
            "docs_used": 0,
            "docs_limit": 100,  # Free plan limit
            "is_locked": False,
            "plan_code": "free",
            "subscription_active": False,
        }
    
    # Get plan
    result = await db.execute(
        select(BillingPlan).where(BillingPlan.id == subscription.plan_id)
    )
    plan = result.scalar_one_or_none()
    
    # Get current usage
    from app.models import UsageCycle
    
    current_month = datetime.utcnow().strftime("%Y-%m")
    result = await db.execute(
        select(UsageCycle)
        .where(
            UsageCycle.subscription_id == subscription.id,
            UsageCycle.month_year == current_month,
        )
    )
    usage = result.scalar_one_or_none()
    
    return {
        "month_year": current_month,
        "docs_used": usage.docs_used if usage else 0,
        "docs_limit": plan.doc_limit if plan else 0,
        "is_locked": usage.is_locked if usage else False,
        "plan_code": plan.code.value if plan else "unknown",
        "subscription_active": subscription.status == SubscriptionStatus.ACTIVE,
        "overage_docs": usage.overage_docs if usage else 0,
        "overage_charged_cents": usage.overage_charged_cents if usage else 0,
    }


@router.get(
    "/quota",
    summary="Check quota availability",
    description="Check if organization has available document quota. Returns 402 if locked.",
)
async def check_quota(
    db: AsyncSession = Depends(get_db),
    user_org: tuple = Depends(get_current_user_with_org),
) -> dict:
    """
    Check if organization has quota available for document processing.
    
    Returns quota status. HTTP 402 (Payment Required) if quota is exhausted.
    This endpoint is used before document uploads to prevent failed processing.
    """
    user, org_id = user_org
    
    # Get subscription
    result = await db.execute(
        select(Subscription)
        .where(Subscription.organization_id == org_id)
    )
    subscription = result.scalar_one_or_none()
    
    # Get plan
    plan = None
    if subscription:
        result = await db.execute(
            select(BillingPlan).where(BillingPlan.id == subscription.plan_id)
        )
        plan = result.scalar_one_or_none()
    
    # Get current usage
    from app.models import UsageCycle
    
    current_month = datetime.utcnow().strftime("%Y-%m")
    usage = None
    
    if subscription:
        result = await db.execute(
            select(UsageCycle)
            .where(
                UsageCycle.subscription_id == subscription.id,
                UsageCycle.month_year == current_month,
            )
        )
        usage = result.scalar_one_or_none()
    
    # Calculate available
    docs_limit = plan.doc_limit if plan else 100
    docs_used = usage.docs_used if usage else 0
    
    # Check availability
    available = docs_limit == 0 or docs_used < docs_limit
    is_locked = usage.is_locked if usage else False
    subscription_active = subscription is None or subscription.status == SubscriptionStatus.ACTIVE
    
    response = {
        "available": available and subscription_active and not is_locked,
        "docs_used": docs_used,
        "docs_limit": docs_limit,
        "is_locked": is_locked,
        "plan_code": plan.code.value if plan else "free",
        "subscription_active": subscription_active,
        "message": "OK" if available and subscription_active else "Quota exhausted or subscription inactive",
    }
    
    # Return 402 if not available
    if not available or not subscription_active or is_locked:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "type": "https://api.pranely.com/errors/billing",
                "title": "Quota exceeded",
                "status": 402,
                "detail": response["message"],
                "used": docs_used,
                "limit": docs_limit,
            },
        )
    
    return response


# Import webhook router and include it
from app.api.v1.billing.webhook import router as webhook_router

router.include_router(webhook_router)