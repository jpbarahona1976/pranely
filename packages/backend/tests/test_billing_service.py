"""Tests for billing service layer."""
import pytest
from datetime import datetime, timezone

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
)
from app.services.billing import BillingService


@pytest.fixture
async def billing_service(db_session):
    """Create billing service instance."""
    return BillingService(db_session)


@pytest.fixture
async def org_with_sub(db_session, billing_plans):
    """Create organization with active subscription."""
    org = Organization(name="Test Org", is_active=True, stripe_customer_id="cus_test123")
    db_session.add(org)
    await db_session.flush()
    
    pro_plan = next(p for p in billing_plans if p.code == BillingPlanCode.PRO)
    
    sub = Subscription(
        organization_id=org.id,
        plan_id=pro_plan.id,
        stripe_customer_id="cus_test123",
        stripe_sub_id="sub_test123",
        status=SubscriptionStatus.ACTIVE,
    )
    db_session.add(sub)
    await db_session.flush()
    
    # Add usage cycle
    current_month = datetime.utcnow().strftime("%Y-%m")
    usage = UsageCycle(
        subscription_id=sub.id,
        month_year=current_month,
        docs_used=50,
        docs_limit=pro_plan.doc_limit,
    )
    db_session.add(usage)
    
    await db_session.commit()
    
    return {"org": org, "subscription": sub, "usage": usage}


@pytest.fixture
async def org_no_sub(db_session):
    """Create organization without subscription (free tier)."""
    org = Organization(name="Free Org", is_active=True)
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


class TestBillingServiceSubscription:
    """Tests for subscription management."""

    @pytest.mark.asyncio
    async def test_get_subscription_returns_sub(self, billing_service, org_with_sub):
        """Test get_subscription returns existing subscription."""
        sub = await billing_service.get_subscription(org_with_sub["org"].id)
        assert sub is not None
        assert sub.organization_id == org_with_sub["org"].id
        assert sub.status == SubscriptionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_get_subscription_returns_none_for_no_sub(self, billing_service, org_no_sub):
        """Test get_subscription returns None when no subscription."""
        sub = await billing_service.get_subscription(org_no_sub.id)
        assert sub is None

    @pytest.mark.asyncio
    async def test_get_or_create_usage_cycle_creates_new(self, billing_service, org_with_sub):
        """Test get_or_create_usage_cycle creates new cycle if not exists."""
        sub = org_with_sub["subscription"]
        
        # Request a different month
        usage = await billing_service.get_or_create_usage_cycle(sub, "2025-01")
        
        assert usage is not None
        assert usage.month_year == "2025-01"
        assert usage.docs_limit == 2500  # Pro plan limit

    @pytest.mark.asyncio
    async def test_get_or_create_usage_cycle_returns_existing(self, billing_service, org_with_sub):
        """Test get_or_create_usage_cycle returns existing cycle."""
        sub = org_with_sub["subscription"]
        existing_usage = org_with_sub["usage"]
        current_month = datetime.utcnow().strftime("%Y-%m")
        
        usage = await billing_service.get_or_create_usage_cycle(sub, current_month)
        
        assert usage.id == existing_usage.id
        assert usage.docs_used == 50  # Original value


class TestBillingServiceQuota:
    """Tests for quota checking."""

    @pytest.mark.asyncio
    async def test_check_quota_available_active_sub(self, billing_service, org_with_sub):
        """Test quota check returns available for active subscription."""
        available, message = await billing_service.check_quota_available(org_with_sub["org"].id)
        assert available is True
        assert "OK" in message

    @pytest.mark.asyncio
    async def test_check_quota_available_no_sub(self, billing_service, org_no_sub):
        """Test quota check returns available for no subscription (free tier)."""
        available, message = await billing_service.check_quota_available(org_no_sub.id)
        assert available is True
        assert "free tier" in message.lower()

    @pytest.mark.asyncio
    async def test_check_quota_exhausted(self, billing_service, db_session, billing_plans, org_no_sub):
        """Test quota check returns not available when exhausted."""
        # Get free plan
        free_plan = next(p for p in billing_plans if p.code == BillingPlanCode.FREE)
        
        # Create subscription with usage at limit
        sub = Subscription(
            organization_id=org_no_sub.id,
            plan_id=free_plan.id,
            status=SubscriptionStatus.ACTIVE,
        )
        db_session.add(sub)
        await db_session.flush()
        
        current_month = datetime.utcnow().strftime("%Y-%m")
        usage = UsageCycle(
            subscription_id=sub.id,
            month_year=current_month,
            docs_used=100,  # At limit
            docs_limit=100,  # Free plan limit
        )
        db_session.add(usage)
        await db_session.commit()
        
        available, message = await billing_service.check_quota_available(org_no_sub.id)
        assert available is False
        assert "exceeded" in message.lower()

    @pytest.mark.asyncio
    async def test_check_quota_locked_cycle(self, billing_service, db_session, billing_plans, org_no_sub):
        """Test quota check returns not available when cycle is locked."""
        free_plan = next(p for p in billing_plans if p.code == BillingPlanCode.FREE)
        
        sub = Subscription(
            organization_id=org_no_sub.id,
            plan_id=free_plan.id,
            status=SubscriptionStatus.ACTIVE,
        )
        db_session.add(sub)
        await db_session.flush()
        
        current_month = datetime.utcnow().strftime("%Y-%m")
        usage = UsageCycle(
            subscription_id=sub.id,
            month_year=current_month,
            docs_used=50,
            docs_limit=100,
            is_locked=True,  # Locked
        )
        db_session.add(usage)
        await db_session.commit()
        
        available, message = await billing_service.check_quota_available(org_no_sub.id)
        assert available is False
        assert "locked" in message.lower()

    @pytest.mark.asyncio
    async def test_check_quota_inactive_subscription(self, billing_service, db_session, billing_plans, org_no_sub):
        """Test quota check returns not available for inactive subscription."""
        free_plan = next(p for p in billing_plans if p.code == BillingPlanCode.FREE)
        
        sub = Subscription(
            organization_id=org_no_sub.id,
            plan_id=free_plan.id,
            status=SubscriptionStatus.PAST_DUE,  # Inactive
        )
        db_session.add(sub)
        await db_session.commit()
        
        available, message = await billing_service.check_quota_available(org_no_sub.id)
        assert available is False


class TestBillingServiceIncrementUsage:
    """Tests for usage incrementing."""

    @pytest.mark.asyncio
    async def test_increment_usage_success(self, billing_service, org_with_sub):
        """Test increment usage increases counter."""
        org_id = org_with_sub["org"].id
        initial_used = org_with_sub["usage"].docs_used
        
        result = await billing_service.increment_usage(org_id, 5)
        
        assert result is True
        
        # Refresh and verify
        await db_session.refresh(org_with_sub["usage"])
        assert org_with_sub["usage"].docs_used == initial_used + 5

    @pytest.mark.asyncio
    async def test_increment_usage_no_quota(self, billing_service, db_session, billing_plans, org_no_sub):
        """Test increment usage returns False when no quota."""
        free_plan = next(p for p in billing_plans if p.code == BillingPlanCode.FREE)
        
        sub = Subscription(
            organization_id=org_no_sub.id,
            plan_id=free_plan.id,
            status=SubscriptionStatus.ACTIVE,
        )
        db_session.add(sub)
        await db_session.flush()
        
        current_month = datetime.utcnow().strftime("%Y-%m")
        usage = UsageCycle(
            subscription_id=sub.id,
            month_year=current_month,
            docs_used=100,  # At limit
            docs_limit=100,
        )
        db_session.add(usage)
        await db_session.commit()
        
        result = await billing_service.increment_usage(org_no_sub.id, 1)
        assert result is False

    @pytest.mark.asyncio
    async def test_increment_usage_no_sub(self, billing_service, org_no_sub):
        """Test increment usage returns True for no subscription (free tier tracking not needed)."""
        result = await billing_service.increment_usage(org_no_sub.id, 1)
        assert result is True  # No tracking for free tier


class TestBillingServiceSyncSubscription:
    """Tests for Stripe subscription sync."""

    @pytest.mark.asyncio
    async def test_sync_subscription_creates_new(self, billing_service, db_session, billing_plans):
        """Test sync_subscription creates new subscription."""
        # Create org without stripe_customer_id first
        org = Organization(name="New Stripe Org", is_active=True, stripe_customer_id="cus_new456")
        db_session.add(org)
        await db_session.flush()
        
        # Sync from Stripe data
        subscription = await billing_service.sync_subscription_from_stripe(
            stripe_customer_id="cus_new456",
            stripe_sub_id="sub_new123",
            plan_code="pro",
            period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            period_end=datetime(2026, 2, 1, tzinfo=timezone.utc),
            status="active",
        )
        
        assert subscription is not None
        assert subscription.organization_id == org.id
        assert subscription.status == SubscriptionStatus.ACTIVE
        assert subscription.stripe_sub_id == "sub_new123"

    @pytest.mark.asyncio
    async def test_sync_subscription_updates_existing(self, billing_service, org_with_sub):
        """Test sync_subscription updates existing subscription."""
        sub = org_with_sub["subscription"]
        
        updated_sub = await billing_service.sync_subscription_from_stripe(
            stripe_customer_id="cus_test123",
            stripe_sub_id="sub_upgraded",
            plan_code="enterprise",
            status="active",
        )
        
        assert updated_sub is not None
        assert updated_sub.id == sub.id
        assert updated_sub.stripe_sub_id == "sub_upgraded"

    @pytest.mark.asyncio
    async def test_sync_subscription_unknown_customer(self, billing_service):
        """Test sync_subscription returns None for unknown customer."""
        result = await billing_service.sync_subscription_from_stripe(
            stripe_customer_id="cus_unknown",
            stripe_sub_id="sub_unknown",
            plan_code="pro",
        )
        
        assert result is None


class TestBillingServiceCancel:
    """Tests for subscription cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_subscription_success(self, billing_service, org_with_sub):
        """Test cancel_subscription cancels active subscription."""
        result = await billing_service.cancel_subscription(org_with_sub["org"].id)
        
        assert result is True
        
        await db_session.refresh(org_with_sub["subscription"])
        assert org_with_sub["subscription"].status == SubscriptionStatus.CANCELLED
        assert org_with_sub["subscription"].cancelled_at is not None

    @pytest.mark.asyncio
    async def test_cancel_subscription_no_sub(self, billing_service, org_no_sub):
        """Test cancel_subscription returns False for no subscription."""
        result = await billing_service.cancel_subscription(org_no_sub.id)
        assert result is False