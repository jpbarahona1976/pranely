"""Stripe webhook handler with signature verification and idempotency."""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import (
    BillingPlan,
    BillingPlanCode,
    Organization,
    Subscription,
    SubscriptionStatus,
    UsageCycle,
    WebhookEvent,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["Billing Webhook"])


class WebhookResponse(BaseModel):
    """Response for webhook endpoint."""
    received: bool
    event_id: str
    event_type: str
    processed: bool = True
    message: Optional[str] = None


def _verify_stripe_signature(payload: bytes, sig_header: str) -> dict:
    """
    Verify Stripe webhook signature and return event payload.
    
    Raises HTTPException if signature is invalid.
    In production (ENV=production), STRIPE_WEBHOOK_SECRET is required.
    In development, signature verification can be skipped if secret not set.
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        # SECURITY: Block in production if webhook secret not configured
        if settings.ENV == "production":
            logger.error("STRIPE_WEBHOOK_SECRET not set in production environment")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "type": "https://api.pranely.com/errors/billing",
                    "title": "Webhook secret required",
                    "status": 500,
                    "detail": "STRIPE_WEBHOOK_SECRET required in production",
                },
            )
        # In development without webhook secret, skip verification
        logger.warning(
            "STRIPE_WEBHOOK_SECRET not set. Skipping webhook signature verification. "
            "DO NOT use in production!"
        )
        return None
    
    try:
        import stripe
        # Use STRIPE_SECRET_KEY (sk_live_...) for API calls
        # STRIPE_WEBHOOK_SECRET (whsec_...) is only used for signature verification
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET, tolerance=300
        )
        return event
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Stripe signature verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/billing",
                "title": "Invalid signature",
                "status": 400,
                "detail": "Webhook signature verification failed",
            },
        )
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/billing",
                "title": "Webhook processing error",
                "status": 400,
                "detail": str(e),
            },
        )


async def _is_event_processed(db: AsyncSession, event_id: str, event_type: str) -> bool:
    """Check if event was already processed (idempotency check)."""
    result = await db.execute(
        select(WebhookEvent).where(
            WebhookEvent.event_id == event_id,
            WebhookEvent.event_type == event_type,
        )
    )
    return result.scalar_one_or_none() is not None


async def _mark_event_processed(
    db: AsyncSession,
    event_id: str,
    event_type: str,
    stripe_customer_id: Optional[str],
    payload: Optional[dict],
    success: bool = True,
    error_message: Optional[str] = None,
) -> WebhookEvent:
    """Mark event as processed in database."""
    webhook_event = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        stripe_customer_id=stripe_customer_id,
        payload_json=payload,
        success=success,
        error_message=error_message,
    )
    db.add(webhook_event)
    await db.flush()
    return webhook_event


async def _get_subscription_by_stripe_customer(
    db: AsyncSession, stripe_customer_id: str
) -> Optional[Subscription]:
    """Get subscription by Stripe customer ID."""
    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_customer_id == stripe_customer_id
        )
    )
    return result.scalar_one_or_none()


async def _get_subscription_by_stripe_sub_id(
    db: AsyncSession, stripe_sub_id: str
) -> Optional[Subscription]:
    """Get subscription by Stripe subscription ID."""
    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_sub_id == stripe_sub_id
        )
    )
    return result.scalar_one_or_none()


async def _get_organization_by_stripe_customer(
    db: AsyncSession, stripe_customer_id: str
) -> Optional[Organization]:
    """Get organization by Stripe customer ID."""
    result = await db.execute(
        select(Organization).where(
            Organization.stripe_customer_id == stripe_customer_id
        )
    )
    return result.scalar_one_or_none()


async def _get_plan_by_code(db: AsyncSession, code: BillingPlanCode) -> Optional[BillingPlan]:
    """Get billing plan by code."""
    result = await db.execute(
        select(BillingPlan).where(BillingPlan.code == code)
    )
    return result.scalar_one_or_none()


async def _get_or_create_usage_cycle(
    db: AsyncSession, subscription: Subscription, month_year: str
) -> UsageCycle:
    """Get or create usage cycle for the current month."""
    result = await db.execute(
        select(UsageCycle).where(
            UsageCycle.subscription_id == subscription.id,
            UsageCycle.month_year == month_year,
        )
    )
    usage = result.scalar_one_or_none()
    
    if usage is None:
        # Get plan limits
        plan_result = await db.execute(
            select(BillingPlan).where(BillingPlan.id == subscription.plan_id)
        )
        plan = plan_result.scalar_one_or_none()
        
        usage = UsageCycle(
            subscription_id=subscription.id,
            month_year=month_year,
            docs_used=0,
            docs_limit=plan.doc_limit if plan else 100,
        )
        db.add(usage)
        await db.flush()
    
    return usage


async def _handle_checkout_completed(
    db: AsyncSession, event_data: dict
) -> bool:
    """
    Handle checkout.session.completed event.
    
    Creates or updates subscription when checkout completes.
    Supports new customers by linking via metadata.org_id.
    """
    customer_id = event_data.get("customer")
    subscription_id = event_data.get("subscription")
    
    if not customer_id:
        logger.warning("checkout.session.completed: No customer_id")
        return False
    
    # Get organization by stripe_customer_id
    org = await _get_organization_by_stripe_customer(db, customer_id)
    
    # FIX: If org not found by stripe_customer_id, try metadata.org_id
    if org is None:
        metadata = event_data.get("metadata", {})
        org_id_str = metadata.get("org_id")
        
        if org_id_str:
            try:
                org_id = int(org_id_str)
                from sqlalchemy import select as sa_select
                result = await db.execute(
                    sa_select(Organization).where(Organization.id == org_id)
                )
                org = result.scalar_one_or_none()
                
                if org:
                    # Link new customer to existing org
                    org.stripe_customer_id = customer_id
                    logger.info(f"Linked new customer {customer_id} to org {org.id}")
                else:
                    logger.error(f"checkout.session.completed: Org not found for metadata.org_id={org_id}")
                    return False
            except (ValueError, TypeError) as e:
                logger.error(f"checkout.session.completed: Invalid org_id in metadata: {org_id_str}")
                return False
        else:
            logger.error(f"checkout.session.completed: No org found for customer {customer_id} and no metadata.org_id")
            return False
    
    # Determine plan from metadata or line_items
    metadata = event_data.get("metadata", {})
    plan_code_str = metadata.get("plan_code", "free")
    
    try:
        plan_code = BillingPlanCode(plan_code_str)
    except ValueError:
        plan_code = BillingPlanCode.FREE
    
    plan = await _get_plan_by_code(db, plan_code)
    if plan is None:
        logger.error(f"checkout.session.completed: Plan not found: {plan_code}")
        return False
    
    # Check if subscription already exists
    existing_sub = await _get_subscription_by_stripe_customer(db, customer_id)
    
    if existing_sub:
        # Update existing subscription
        existing_sub.plan_id = plan.id
        existing_sub.status = SubscriptionStatus.ACTIVE
        existing_sub.stripe_sub_id = subscription_id
        if subscription_id:
            existing_sub.stripe_sub_id = subscription_id
        
        # Update period dates if available
        subscription_details = event_data.get("subscription_details", {})
        current_period_start = subscription_details.get("current_period_start")
        current_period_end = subscription_details.get("current_period_end")
        
        if current_period_start:
            existing_sub.current_period_start = datetime.fromtimestamp(
                current_period_start, tz=timezone.utc
            )
        if current_period_end:
            existing_sub.current_period_end = datetime.fromtimestamp(
                current_period_end, tz=timezone.utc
            )
    else:
        # Create new subscription
        now = datetime.now(timezone.utc)
        
        # Calculate period end (1 month from now)
        if now.month == 12:
            period_end = now.replace(year=now.year + 1, month=1, day=1)
        else:
            period_end = now.replace(month=now.month + 1, day=1)
        
        new_sub = Subscription(
            organization_id=org.id,
            plan_id=plan.id,
            stripe_customer_id=customer_id,
            stripe_sub_id=subscription_id,
            status=SubscriptionStatus.ACTIVE,
            started_at=now,
            current_period_start=now,
            current_period_end=period_end,
        )
        db.add(new_sub)
        
        # Create initial usage cycle
        month_year = now.strftime("%Y-%m")
        await db.flush()
        
        usage = UsageCycle(
            subscription_id=new_sub.id,
            month_year=month_year,
            docs_used=0,
            docs_limit=plan.doc_limit,
        )
        db.add(usage)
    
    logger.info(f"checkout.session.completed: Subscription created/updated for org {org.id}")
    return True


async def _handle_subscription_updated(
    db: AsyncSession, event_data: dict
) -> bool:
    """
    Handle customer.subscription.updated event.
    
    Updates subscription status and period dates.
    """
    subscription_id = event_data.get("id")
    customer_id = event_data.get("customer")
    status_str = event_data.get("status")
    
    if not subscription_id:
        logger.warning("subscription.updated: No subscription_id")
        return False
    
    # Get subscription
    subscription = await _get_subscription_by_stripe_sub_id(db, subscription_id)
    if subscription is None:
        # Try by customer_id
        subscription = await _get_subscription_by_stripe_customer(db, customer_id)
    
    if subscription is None:
        logger.warning(f"subscription.updated: Subscription not found for {subscription_id}")
        return False
    
    # Map Stripe status to our status
    status_map = {
        "active": SubscriptionStatus.ACTIVE,
        "trialing": SubscriptionStatus.ACTIVE,
        "past_due": SubscriptionStatus.PAST_DUE,
        "canceled": SubscriptionStatus.CANCELLED,
        "unpaid": SubscriptionStatus.PAST_DUE,
    }
    
    new_status = status_map.get(status_str, subscription.status)
    subscription.status = new_status
    
    # Update period dates
    current_period_start = event_data.get("current_period_start")
    current_period_end = event_data.get("current_period_end")
    
    if current_period_start:
        subscription.current_period_start = datetime.fromtimestamp(
            current_period_start, tz=timezone.utc
        )
    if current_period_end:
        subscription.current_period_end = datetime.fromtimestamp(
            current_period_end, tz=timezone.utc
        )
    
    logger.info(f"subscription.updated: Subscription {subscription_id} status updated to {new_status}")
    return True


async def _handle_subscription_deleted(
    db: AsyncSession, event_data: dict
) -> bool:
    """
    Handle customer.subscription.deleted event.
    
    Marks subscription as cancelled.
    """
    subscription_id = event_data.get("id")
    customer_id = event_data.get("customer")
    
    if not subscription_id:
        logger.warning("subscription.deleted: No subscription_id")
        return False
    
    # Get subscription
    subscription = await _get_subscription_by_stripe_sub_id(db, subscription_id)
    if subscription is None:
        subscription = await _get_subscription_by_stripe_customer(db, customer_id)
    
    if subscription is None:
        logger.warning(f"subscription.deleted: Subscription not found for {subscription_id}")
        return False
    
    subscription.status = SubscriptionStatus.CANCELLED
    subscription.cancelled_at = datetime.now(timezone.utc)
    
    logger.info(f"subscription.deleted: Subscription {subscription_id} cancelled")
    return True


@router.post(
    "",
    response_model=WebhookResponse,
    summary="Stripe webhook endpoint",
    description="Receive and process Stripe webhook events.",
)
async def handle_stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    """
    Handle incoming Stripe webhook events.
    
    Verifies signature and processes events idempotently.
    Supported events:
    - checkout.session.completed
    - customer.subscription.updated
    - customer.subscription.deleted
    """
    # Get raw payload and signature
    body = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    # Verify signature
    event = _verify_stripe_signature(body, sig_header)
    
    # If signature verification returned None (dev mode), parse event from body
    if event is None:
        import json
        event = json.loads(body)
    
    event_id = event.get("id")
    event_type = event.get("type")
    event_data = event.get("data", {}).get("object", {})
    
    if not event_id or not event_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/billing",
                "title": "Invalid event",
                "status": 400,
                "detail": "Missing event_id or event_type",
            },
        )
    
    # Check idempotency
    if await _is_event_processed(db, event_id, event_type):
        logger.info(f"Webhook event {event_id} ({event_type}) already processed, skipping")
        return WebhookResponse(
            received=True,
            event_id=event_id,
            event_type=event_type,
            processed=False,
            message="Event already processed (idempotency check)",
        )
    
    # Get stripe customer ID for tracking
    stripe_customer_id = event_data.get("customer")
    
    # Process event based on type
    success = False
    error_message = None
    
    try:
        if event_type == "checkout.session.completed":
            success = await _handle_checkout_completed(db, event_data)
        elif event_type == "customer.subscription.updated":
            success = await _handle_subscription_updated(db, event_data)
        elif event_type == "customer.subscription.deleted":
            success = await _handle_subscription_deleted(db, event_data)
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")
    except Exception as e:
        logger.error(f"Error processing webhook event {event_id}: {e}")
        success = False
        error_message = str(e)
    
    # Mark event as processed (always, even if handling failed)
    await _mark_event_processed(
        db,
        event_id,
        event_type,
        stripe_customer_id,
        event.get("data", {}),
        success=success,
        error_message=error_message,
    )
    
    # Commit transaction
    await db.commit()
    
    return WebhookResponse(
        received=True,
        event_id=event_id,
        event_type=event_type,
        processed=success,
        message="Event processed successfully" if success else f"Handler failed: {error_message}",
    )
