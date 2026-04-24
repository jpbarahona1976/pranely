"""Tests for Stripe webhook endpoint."""
import json
import time
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models import (
    BillingPlan,
    BillingPlanCode,
    Organization,
    Subscription,
    SubscriptionStatus,
    UsageCycle,
    User,
    Membership,
    UserRole,
    WebhookEvent,
)


@pytest.fixture
async def test_org(db_session):
    """Create a test organization with Stripe customer ID."""
    org = Organization(
        name="Test Org",
        is_active=True,
        stripe_customer_id="cus_test123",
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest.fixture
async def test_org_no_stripe(db_session):
    """Create a test organization without Stripe customer ID."""
    org = Organization(
        name="Test Org No Stripe",
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest.fixture
async def billing_plans(db_session):
    """Create default billing plans."""
    plans = [
        BillingPlan(
            code=BillingPlanCode.FREE,
            name="Free Plan",
            description="Free tier",
            price_usd_cents=0,
            doc_limit=100,
            doc_limit_period="monthly",
            features_json={"basic": True},
            is_active=True,
        ),
        BillingPlan(
            code=BillingPlanCode.PRO,
            name="Pro Plan",
            description="Professional tier",
            price_usd_cents=2999,
            doc_limit=1000,
            doc_limit_period="monthly",
            features_json={"basic": True, "advanced": True},
            is_active=True,
        ),
    ]
    
    for plan in plans:
        db_session.add(plan)
    
    await db_session.commit()
    return plans


@pytest.fixture
async def test_subscription(db_session, test_org, billing_plans):
    """Create a test subscription."""
    free_plan = next(p for p in billing_plans if p.code == BillingPlanCode.FREE)
    
    subscription = Subscription(
        organization_id=test_org.id,
        plan_id=free_plan.id,
        stripe_customer_id=test_org.stripe_customer_id,
        status=SubscriptionStatus.ACTIVE,
    )
    db_session.add(subscription)
    await db_session.commit()
    await db_session.refresh(subscription)
    return subscription


def _make_mock_stripe_event(event_id: str, event_type: str, data: dict) -> dict:
    """Create a mock Stripe event payload."""
    return {
        "id": event_id,
        "type": event_type,
        "data": {"object": data},
    }


class TestWebhookSignatureVerification:
    """Tests for webhook signature verification."""

    @pytest.mark.asyncio
    async def test_webhook_valid_signature(self, client, db_session, test_org):
        """Test webhook accepts valid signature when secret is set."""
        with patch("app.api.v1.billing.webhook.settings") as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test_secret"
            
            # Mock stripe verification
            with patch("stripe.Webhook.construct_event") as mock_verify:
                mock_verify.return_value = _make_mock_stripe_event(
                    "evt_test123",
                    "checkout.session.completed",
                    {"customer": test_org.stripe_customer_id}
                )
                
                response = await client.post(
                    "/api/v1/billing/webhook",
                    content=json.dumps(mock_verify.return_value),
                    headers={
                        "stripe-signature": "sig_test123",
                        "Content-Type": "application/json",
                    },
                )
        
        # Should accept and process (or skip if org not found)
        assert response.status_code == 200
        data = response.json()
        assert data["received"] is True
        assert data["event_id"] == "evt_test123"

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature(self, client, db_session, test_org):
        """Test webhook rejects invalid signature."""
        import stripe as stripe_lib
        
        with patch("app.api.v1.billing.webhook.settings") as mock_settings:
            mock_settings.STRIPE_WEBHOOK_SECRET = "whsec_test_secret"
            
            # Mock stripe verification to raise error
            with patch.object(stripe_lib, "Webhook") as mock_webhook:
                # Use a simple exception for testing
                mock_webhook.construct_event.side_effect = Exception("Invalid signature")
                
                response = await client.post(
                    "/api/v1/billing/webhook",
                    content=json.dumps({"id": "evt_test", "type": "test"}),
                    headers={
                        "stripe-signature": "invalid_signature",
                        "Content-Type": "application/json",
                    },
                )
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid signature" in str(data)


class TestWebhookIdempotency:
    """Tests for webhook idempotency."""

    @pytest.mark.asyncio
    async def test_webhook_duplicate_event_rejected(self, client, db_session, test_org, billing_plans):
        """Test that duplicate webhook events are rejected (idempotency)."""
        event_id = "evt_duplicate_test123"
        event_type = "checkout.session.completed"
        
        # First, mark the event as processed
        webhook_event = WebhookEvent(
            event_id=event_id,
            event_type=event_type,
            stripe_customer_id=test_org.stripe_customer_id,
            success=True,
        )
        db_session.add(webhook_event)
        await db_session.commit()
        
        # Now send the same event again
        event_data = _make_mock_stripe_event(
            event_id,
            event_type,
            {
                "customer": test_org.stripe_customer_id,
                "subscription": "sub_test123",
                "metadata": {"plan_code": "free"},
            }
        )
        
        response = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event_data),
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["received"] is True
        assert data["processed"] is False
        assert "already processed" in data["message"]

    @pytest.mark.asyncio
    async def test_webhook_event_stored(self, client, db_session, test_org):
        """Test that processed webhook events are stored."""
        event_id = "evt_stored_test123"
        event_type = "checkout.session.completed"
        
        event_data = _make_mock_stripe_event(
            event_id,
            event_type,
            {"customer": test_org.stripe_customer_id}
        )
        
        response = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event_data),
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 200
        
        # Verify event was stored
        result = await db_session.execute(
            select(WebhookEvent).where(
                WebhookEvent.event_id == event_id,
                WebhookEvent.event_type == event_type,
            )
        )
        stored_event = result.scalar_one_or_none()
        assert stored_event is not None


class TestCheckoutSessionCompleted:
    """Tests for checkout.session.completed event handling."""

    @pytest.mark.asyncio
    async def test_checkout_completed_creates_subscription(
        self, client, db_session, test_org_no_stripe, billing_plans
    ):
        """Test that checkout.completed creates subscription for org without Stripe ID."""
        event_id = "evt_checkout_completed123"
        
        event_data = _make_mock_stripe_event(
            event_id,
            "checkout.session.completed",
            {
                "customer": "cus_new_customer",
                "subscription": "sub_new123",
                "metadata": {"plan_code": "pro"},
                "subscription_details": {
                    "current_period_start": int(time.time()),
                    "current_period_end": int(time.time()) + 2592000,  # +30 days
                },
            }
        )
        
        # First set the stripe_customer_id on the org
        test_org_no_stripe.stripe_customer_id = "cus_new_customer"
        await db_session.commit()
        
        response = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event_data),
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["received"] is True
        assert data["event_type"] == "checkout.session.completed"
        
        # Verify subscription was created
        result = await db_session.execute(
            select(Subscription).where(
                Subscription.stripe_customer_id == "cus_new_customer"
            )
        )
        subscription = result.scalar_one_or_none()
        assert subscription is not None
        assert subscription.status == SubscriptionStatus.ACTIVE
        
        # Verify usage cycle was created
        result = await db_session.execute(
            select(UsageCycle).where(
                UsageCycle.subscription_id == subscription.id
            )
        )
        usage = result.scalar_one_or_none()
        assert usage is not None
        assert usage.docs_limit == 1000  # Pro plan limit

    @pytest.mark.asyncio
    async def test_checkout_completed_updates_existing_subscription(
        self, client, db_session, test_org, billing_plans, test_subscription
    ):
        """Test that checkout.completed updates existing subscription."""
        event_id = "evt_checkout_update123"
        
        # Upgrade to Pro plan
        pro_plan = next(p for p in billing_plans if p.code == BillingPlanCode.PRO)
        
        event_data = _make_mock_stripe_event(
            event_id,
            "checkout.session.completed",
            {
                "customer": test_org.stripe_customer_id,
                "subscription": "sub_upgraded123",
                "metadata": {"plan_code": "pro"},
            }
        )
        
        response = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event_data),
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 200
        
        # Verify subscription was updated to Pro
        await db_session.refresh(test_subscription)
        assert test_subscription.plan_id == pro_plan.id
        assert test_subscription.status == SubscriptionStatus.ACTIVE


class TestSubscriptionUpdated:
    """Tests for customer.subscription.updated event handling."""

    @pytest.mark.asyncio
    async def test_subscription_updated_changes_status(
        self, client, db_session, test_org, billing_plans, test_subscription
    ):
        """Test that subscription.updated changes subscription status."""
        event_id = "evt_sub_updated123"
        
        event_data = _make_mock_stripe_event(
            event_id,
            "customer.subscription.updated",
            {
                "id": test_subscription.stripe_sub_id or "sub_test123",
                "customer": test_org.stripe_customer_id,
                "status": "past_due",
            }
        )
        
        # Set stripe_sub_id first
        test_subscription.stripe_sub_id = "sub_test123"
        await db_session.commit()
        
        response = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event_data),
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 200
        
        # Verify status changed to past_due
        await db_session.refresh(test_subscription)
        assert test_subscription.status == SubscriptionStatus.PAST_DUE

    @pytest.mark.asyncio
    async def test_subscription_updated_unknown_subscription(
        self, client, db_session
    ):
        """Test that subscription.updated handles unknown subscription gracefully."""
        event_id = "evt_sub_unknown123"
        
        event_data = _make_mock_stripe_event(
            event_id,
            "customer.subscription.updated",
            {
                "id": "sub_unknown",
                "customer": "cus_unknown",
                "status": "active",
            }
        )
        
        response = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event_data),
            headers={"Content-Type": "application/json"},
        )
        
        # Should still return 200 (event was received)
        assert response.status_code == 200
        data = response.json()
        assert data["received"] is True


class TestSubscriptionDeleted:
    """Tests for customer.subscription.deleted event handling."""

    @pytest.mark.asyncio
    async def test_subscription_deleted_cancels_subscription(
        self, client, db_session, test_org, billing_plans, test_subscription
    ):
        """Test that subscription.deleted cancels the subscription."""
        event_id = "evt_sub_deleted123"
        
        # Set stripe_sub_id
        test_subscription.stripe_sub_id = "sub_to_delete"
        await db_session.commit()
        
        event_data = _make_mock_stripe_event(
            event_id,
            "customer.subscription.deleted",
            {
                "id": "sub_to_delete",
                "customer": test_org.stripe_customer_id,
            }
        )
        
        response = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event_data),
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 200
        
        # Verify subscription was cancelled
        await db_session.refresh(test_subscription)
        assert test_subscription.status == SubscriptionStatus.CANCELLED
        assert test_subscription.cancelled_at is not None


class TestWebhookSecurity:
    """Security tests for webhook endpoint."""

    @pytest.mark.asyncio
    async def test_webhook_missing_event_id(self, client, db_session):
        """Test that webhook rejects events without event_id."""
        event_data = {
            "type": "checkout.session.completed",
            "data": {"object": {}},
        }
        
        response = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event_data),
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_missing_event_type(self, client, db_session):
        """Test that webhook rejects events without event_type."""
        event_data = {
            "id": "evt_test123",
            "data": {"object": {}},
        }
        
        response = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event_data),
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_unhandled_event_type(self, client, db_session):
        """Test that webhook handles unhandled event types gracefully."""
        event_id = "evt_unhandled123"
        
        event_data = _make_mock_stripe_event(
            event_id,
            "invoice.payment_failed",  # Not handled
            {"customer": "cus_test"}
        )
        
        response = await client.post(
            "/api/v1/billing/webhook",
            content=json.dumps(event_data),
            headers={"Content-Type": "application/json"},
        )
        
        # Should still return 200 (event was received and stored)
        assert response.status_code == 200
        data = response.json()
        assert data["received"] is True
        assert data["event_type"] == "invoice.payment_failed"
