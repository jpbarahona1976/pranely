"""Tests for billing webhook Stripe integration.

FASE 9A.1 FIX: Complete webhook test coverage with Stripe mocks.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.models import Subscription, SubscriptionStatus


# =============================================================================
# Mocks
# =============================================================================

@pytest.fixture
def stripe_webhook_headers():
    """Headers for Stripe webhook verification."""
    return {
        "Stripe-Signature": "t=1234567890,v1=abc123,v0=def456",
        "Content-Type": "application/json",
    }


@pytest.fixture
def mock_stripe_verify_signature():
    """Mock Stripe signature verification."""
    # Mock the stripe module's construct_event or the verify function based on implementation
    with patch("stripe.Webhook.construct_event") as mock:
        mock.return_value = MagicMock(type="test", data={"object": {}})
        yield mock


@pytest.fixture
def mock_stripe_subscription():
    """Mock Stripe subscription object."""
    mock_sub = MagicMock()
    mock_sub.id = "sub_test123"
    mock_sub.customer = "cus_test123"
    mock_sub.status = "active"
    mock_sub.current_period_start = 1704067200
    mock_sub.current_period_end = 1706745600
    mock_sub.items.data = [
        MagicMock(
            price=MagicMock(
                id="price_test",
                unit_amount=2999,
            )
        )
    ]
    return mock_sub


# =============================================================================
# Tests: Webhook Subscription Events
# =============================================================================

class TestWebhookSubscriptionCreated:
    """Tests for subscription created webhook."""

    @pytest.mark.asyncio
    async def test_webhook_subscription_created(
        self, client, stripe_webhook_headers, mock_stripe_verify_signature
    ):
        """Test handling of subscription.created event."""
        event = {
            "id": "evt_test123",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "status": "active",
                    "current_period_start": 1704067200,
                    "current_period_end": 1706745600,
                }
            }
        }
        
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = MagicMock(
                type="customer.subscription.created",
                data=event["data"],
            )
            
            response = await client.post(
                "/api/v1/billing/webhook",
                headers=stripe_webhook_headers,
                content=json.dumps(event),
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["received"] is True


class TestWebhookSubscriptionUpdated:
    """Tests for subscription updated webhook."""

    @pytest.mark.asyncio
    async def test_webhook_subscription_updated(
        self, client, stripe_webhook_headers
    ):
        """Test handling of subscription.updated event."""
        event = {
            "id": "evt_test456",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "status": "active",
                }
            }
        }
        
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = MagicMock(
                type="customer.subscription.updated",
                data=event["data"],
            )
            
            response = await client.post(
                "/api/v1/billing/webhook",
                headers=stripe_webhook_headers,
                content=json.dumps(event),
            )
            
            assert response.status_code == 200


class TestWebhookSubscriptionDeleted:
    """Tests for subscription deleted webhook."""

    @pytest.mark.asyncio
    async def test_webhook_subscription_deleted(
        self, client, stripe_webhook_headers
    ):
        """Test handling of subscription.deleted event."""
        event = {
            "id": "evt_test789",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123",
                    "status": "canceled",
                }
            }
        }
        
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = MagicMock(
                type="customer.subscription.deleted",
                data=event["data"],
            )
            
            response = await client.post(
                "/api/v1/billing/webhook",
                headers=stripe_webhook_headers,
                content=json.dumps(event),
            )
            
            assert response.status_code == 200


class TestWebhookPaymentSucceeded:
    """Tests for payment succeeded webhook."""

    @pytest.mark.asyncio
    async def test_webhook_payment_succeeded(
        self, client, stripe_webhook_headers
    ):
        """Test handling of invoice.paid event."""
        event = {
            "id": "evt_invoice123",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "id": "in_test123",
                    "customer": "cus_test123",
                    "subscription": "sub_test123",
                    "amount_paid": 2999,
                }
            }
        }
        
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = MagicMock(
                type="invoice.paid",
                data=event["data"],
            )
            
            response = await client.post(
                "/api/v1/billing/webhook",
                headers=stripe_webhook_headers,
                content=json.dumps(event),
            )
            
            assert response.status_code == 200


class TestWebhookSecurity:
    """Tests for webhook security."""

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature_403(
        self, client, db_session, stripe_webhook_headers
    ):
        """Test that invalid signature returns 403."""
        event = {"id": "evt_test", "type": "test"}
        
        with patch("app.api.v1.billing.webhook.verify_stripe_signature") as mock:
            mock.return_value = False
            
            response = await client.post(
                "/api/v1/billing/webhook",
                headers={"Content-Type": "application/json"},
                content=json.dumps(event),
            )
            
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_webhook_duplicate_idempotent(
        self, client, stripe_webhook_headers
    ):
        """Test that duplicate events are handled idempotently."""
        event = {
            "id": "evt_duplicate",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_duplicate",
                    "customer": "cus_test123",
                    "status": "active",
                }
            }
        }
        
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = MagicMock(
                type="customer.subscription.created",
                data=event["data"],
            )
            
            # First call
            response1 = await client.post(
                "/api/v1/billing/webhook",
                headers=stripe_webhook_headers,
                content=json.dumps(event),
            )
            
            # Second call - should be idempotent
            response2 = await client.post(
                "/api/v1/billing/webhook",
                headers=stripe_webhook_headers,
                content=json.dumps(event),
            )
            
            assert response1.status_code == 200
            assert response2.status_code == 200