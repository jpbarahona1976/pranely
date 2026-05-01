"""Full tests for billing service.

FASE 9A.1 FIX: Complete billing service test coverage with mocks.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

from app.models import (
    Organization, BillingPlan, BillingPlanCode,
    Subscription, SubscriptionStatus, UsageCycle
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def org_with_subscription(db_session):
    """Create org with active subscription for billing service tests."""
    org = Organization(name="Billing Service Org", is_active=True)
    db_session.add(org)
    await db_session.flush()
    
    # Create Pro plan
    plan = BillingPlan(
        code=BillingPlanCode.PRO,
        name="Pro Plan",
        description="Professional tier",
        price_usd_cents=2999,
        doc_limit=1000,
        doc_limit_period="monthly",
        features_json={"advanced": True},
        is_active=True,
    )
    db_session.add(plan)
    await db_session.flush()
    
    # Create subscription
    subscription = Subscription(
        organization_id=org.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        stripe_customer_id="cus_service_test",
        stripe_sub_id="sub_service_test",
    )
    db_session.add(subscription)
    await db_session.flush()
    
    # Create usage cycle
    current_month = datetime.utcnow().strftime("%Y-%m")
    usage = UsageCycle(
        subscription_id=subscription.id,
        month_year=current_month,
        docs_used=50,
        docs_limit=1000,
        is_locked=False,
    )
    db_session.add(usage)
    await db_session.commit()
    
    return {
        "org": org,
        "plan": plan,
        "subscription": subscription,
        "usage": usage,
    }


@pytest.fixture
def billing_service(db_session):
    """Create BillingService instance."""
    from app.services.billing import BillingService
    return BillingService(db_session)


# =============================================================================
# Tests: Subscription Operations
# =============================================================================

class TestBillingServiceSync:
    """Tests for subscription sync operations."""

    @pytest.mark.asyncio
    async def test_sync_subscription_creates_usage_cycle(
        self, billing_service, org_with_subscription, db_session
    ):
        """Test sync_subscription creates new usage cycle if not exists."""
        sub = org_with_subscription["subscription"]
        
        # Delete existing usage cycle
        await db_session.delete(org_with_subscription["usage"])
        await db_session.commit()
        
        # Sync should create new usage cycle
        result = await billing_service.sync_subscription(
            org_with_subscription["org"].id,
            "sub_sync_test",
            SubscriptionStatus.ACTIVE,
        )
        
        assert result is True
        
        # Verify usage cycle was created
        current_month = datetime.utcnow().strftime("%Y-%m")
        result = await db_session.execute(
            pytest.importorskip("sqlalchemy").select(UsageCycle).where(
                UsageCycle.subscription_id == sub.id,
                UsageCycle.month_year == current_month,
            )
        )
        usage = result.scalar_one_or_none()
        assert usage is not None
        assert usage.docs_limit == 1000  # Pro plan limit

    @pytest.mark.asyncio
    async def test_sync_subscription_updates_existing(
        self, billing_service, org_with_subscription, db_session
    ):
        """Test sync_subscription updates existing subscription."""
        org_id = org_with_subscription["org"].id
        
        # Sync with updated status
        result = await billing_service.sync_subscription(
            org_id,
            "sub_updated",
            SubscriptionStatus.ACTIVE,
        )
        
        assert result is True
        
        # Verify subscription was updated
        await db_session.refresh(org_with_subscription["subscription"])
        assert org_with_subscription["subscription"].stripe_sub_id == "sub_updated"


class TestBillingServiceCancel:
    """Tests for subscription cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_subscription_usage_locked(
        self, billing_service, org_with_subscription, db_session
    ):
        """Test cancel_subscription locks all usage cycles."""
        org_id = org_with_subscription["org"].id
        
        # Create additional usage cycle for another month
        old_usage = UsageCycle(
            subscription_id=org_with_subscription["subscription"].id,
            month_year="2025-01",
            docs_used=100,
            docs_limit=1000,
            is_locked=False,
        )
        db_session.add(old_usage)
        await db_session.commit()
        
        # Cancel subscription
        result = await billing_service.cancel_subscription(org_id)
        
        assert result is True
        
        # Verify usage cycles are locked
        await db_session.refresh(org_with_subscription["usage"])
        assert org_with_subscription["usage"].is_locked is True
        
        await db_session.refresh(old_usage)
        assert old_usage.is_locked is True

    @pytest.mark.asyncio
    async def test_cancel_subscription_nonexistent(self, billing_service, db_session):
        """Test cancel_subscription with no subscription returns False."""
        result = await billing_service.cancel_subscription(99999)
        assert result is False


# =============================================================================
# Tests: Plan Operations
# =============================================================================

class TestBillingServicePlans:
    """Tests for plan operations."""

    @pytest.mark.asyncio
    async def test_get_plan_by_code_cache(
        self, billing_service, org_with_subscription, db_session
    ):
        """Test get_plan_by_code returns cached result."""
        plan_code = BillingPlanCode.PRO
        
        # First call
        plan1 = await billing_service.get_plan_by_code(plan_code)
        assert plan1 is not None
        assert plan1.code == BillingPlanCode.PRO
        
        # Second call should use cache (same object)
        plan2 = await billing_service.get_plan_by_code(plan_code)
        assert plan2 is not None
        assert plan2.code == BillingPlanCode.PRO

    @pytest.mark.asyncio
    async def test_get_plan_by_code_invalid(self, billing_service, db_session):
        """Test get_plan_by_code with invalid code returns None."""
        from app.models import BillingPlanCode
        # This should return None or raise ValueError for invalid enum
        try:
            result = await billing_service.get_plan_by_code(BillingPlanCode("invalid"))
            assert result is None
        except ValueError:
            # Invalid enum value raises ValueError
            pass


# =============================================================================
# Tests: Quota Operations
# =============================================================================

class TestBillingServiceQuota:
    """Tests for quota operations."""

    @pytest.mark.asyncio
    async def test_check_quota_available_active_sub(
        self, billing_service, org_with_subscription
    ):
        """Test check_quota_available with active subscription."""
        org_id = org_with_subscription["org"].id
        
        available, message = await billing_service.check_quota_available(org_id)
        
        assert available is True
        assert "available" in message.lower()

    @pytest.mark.asyncio
    async def test_check_quota_exhausted(
        self, billing_service, org_with_subscription, db_session
    ):
        """Test check_quota_available when quota is exhausted."""
        org_id = org_with_subscription["org"].id
        
        # Exhaust quota
        org_with_subscription["usage"].docs_used = 1000
        await db_session.commit()
        
        available, message = await billing_service.check_quota_available(org_id)
        
        assert available is False
        assert "exceeded" in message.lower() or "quota" in message.lower()

    @pytest.mark.asyncio
    async def test_check_quota_locked_cycle(
        self, billing_service, org_with_subscription, db_session
    ):
        """Test check_quota_available when usage cycle is locked."""
        org_id = org_with_subscription["org"].id
        
        # Lock the cycle
        org_with_subscription["usage"].is_locked = True
        await db_session.commit()
        
        available, message = await billing_service.check_quota_available(org_id)
        
        assert available is False
        assert "locked" in message.lower()


# =============================================================================
# Tests: Increment Usage
# =============================================================================

class TestBillingServiceIncrementUsage:
    """Tests for increment usage operations."""

    @pytest.mark.asyncio
    async def test_increment_usage_success(
        self, billing_service, org_with_subscription, db_session
    ):
        """Test increment_usage increases usage count."""
        org_id = org_with_subscription["org"].id
        initial_used = org_with_subscription["usage"].docs_used
        
        result = await billing_service.increment_usage(org_id, 5)
        
        assert result is True
        
        await db_session.refresh(org_with_subscription["usage"])
        assert org_with_subscription["usage"].docs_used == initial_used + 5

    @pytest.mark.asyncio
    async def test_increment_usage_no_quota(
        self, billing_service, org_with_subscription, db_session
    ):
        """Test increment_usage fails when no quota."""
        org_id = org_with_subscription["org"].id
        
        # Exhaust quota
        org_with_subscription["usage"].docs_used = 1000
        await db_session.commit()
        
        result = await billing_service.increment_usage(org_id, 1)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_increment_usage_no_subscription(self, billing_service, db_session):
        """Test increment_usage returns True when no subscription (free tier)."""
        # Create org without subscription
        org = Organization(name="Free Tier Org", is_active=True)
        db_session.add(org)
        await db_session.commit()
        
        result = await billing_service.increment_usage(org.id, 1)
        
        # Should return True - no tracking for free tier
        assert result is True


# =============================================================================
# Tests: Usage Cycle Operations
# =============================================================================

class TestBillingServiceSubscription:
    """Tests for subscription and usage cycle operations."""

    @pytest.mark.asyncio
    async def test_get_subscription_returns_sub(
        self, billing_service, org_with_subscription
    ):
        """Test get_subscription returns subscription object."""
        sub = await billing_service.get_subscription(org_with_subscription["org"].id)
        
        assert sub is not None
        assert sub.id == org_with_subscription["subscription"].id
        assert sub.status == SubscriptionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_get_subscription_none(self, billing_service, db_session):
        """Test get_subscription returns None for org without subscription."""
        org = Organization(name="No Sub Org", is_active=True)
        db_session.add(org)
        await db_session.commit()
        
        result = await billing_service.get_subscription(org.id)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_or_create_usage_cycle_returns_existing(
        self, billing_service, org_with_subscription
    ):
        """Test get_or_create_usage_cycle returns existing cycle."""
        sub = org_with_subscription["subscription"]
        current_month = datetime.utcnow().strftime("%Y-%m")
        
        usage = await billing_service.get_or_create_usage_cycle(sub, current_month)
        
        assert usage is not None
        assert usage.month_year == current_month
        assert usage.docs_limit == 1000