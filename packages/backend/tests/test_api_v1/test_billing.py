"""Tests for API v1 billing endpoints."""
import pytest

from app.core.security import hash_password
from app.models import (
    BillingPlan, BillingPlanCode, Organization, User, Membership, 
    Subscription, SubscriptionStatus, UserRole
)


@pytest.fixture
async def test_user_org(db_session):
    """Create a test user with organization."""
    org = Organization(name="Test Org", is_active=True)
    db_session.add(org)
    await db_session.flush()
    
    user = User(
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = Membership(
        user_id=user.id,
        organization_id=org.id,
        role=UserRole.OWNER,
    )
    db_session.add(membership)
    await db_session.commit()
    
    return {"user": user, "org": org, "membership": membership}


@pytest.fixture
async def billing_plans(db_session):
    """Create default billing plans."""
    plans = [
        BillingPlan(
            code=BillingPlanCode.FREE,
            name="Free Plan",
            description="Free tier with basic features",
            price_usd_cents=0,
            doc_limit=100,
            doc_limit_period="monthly",
            features_json={"basic": True},
            is_active=True,
        ),
        BillingPlan(
            code=BillingPlanCode.PRO,
            name="Pro Plan",
            description="Professional tier with advanced features",
            price_usd_cents=2999,
            doc_limit=1000,
            doc_limit_period="monthly",
            features_json={"basic": True, "advanced": True},
            is_active=True,
        ),
        BillingPlan(
            code=BillingPlanCode.ENTERPRISE,
            name="Enterprise Plan",
            description="Enterprise tier with all features",
            price_usd_cents=9999,
            doc_limit=0,  # Unlimited
            doc_limit_period="monthly",
            features_json={"basic": True, "advanced": True, "enterprise": True},
            is_active=True,
        ),
    ]
    
    for plan in plans:
        db_session.add(plan)
    
    await db_session.commit()
    
    return plans


@pytest.fixture
async def auth_token(client, test_user_org):
    """Get authentication token for test user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_org["user"].email,
            "password": "testpassword123",
        },
    )
    return response.json()["token"]["access_token"]


class TestBillingPlans:
    """Tests for GET /api/v1/billing/plans."""

    @pytest.mark.asyncio
    async def test_list_plans(self, client, billing_plans, db_session):
        """Test listing available billing plans."""
        response = await client.get("/api/v1/billing/plans")
        
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        assert len(data["plans"]) >= 3
        
        # Verify plan structure
        for plan in data["plans"]:
            assert "code" in plan
            assert "name" in plan
            assert "price_usd_cents" in plan

    @pytest.mark.asyncio
    async def test_list_plans_includes_free(self, client, billing_plans, db_session):
        """Test that free plan is included in list."""
        response = await client.get("/api/v1/billing/plans")
        
        assert response.status_code == 200
        data = response.json()
        plan_codes = [p["code"] for p in data["plans"]]
        assert "free" in plan_codes

    @pytest.mark.asyncio
    async def test_list_plans_ordered_by_price(self, client, billing_plans, db_session):
        """Test that plans are ordered by price."""
        response = await client.get("/api/v1/billing/plans")
        
        assert response.status_code == 200
        data = response.json()
        prices = [p["price_usd_cents"] for p in data["plans"]]
        assert prices == sorted(prices)


class TestBillingSubscription:
    """Tests for GET /api/v1/billing/subscription."""

    @pytest.mark.asyncio
    async def test_get_subscription_authenticated(self, client, auth_token, test_user_org, db_session):
        """Test getting subscription for authenticated user."""
        response = await client.get(
            "/api/v1/billing/subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "plan_code" in data
        assert "status" in data

    @pytest.mark.asyncio
    async def test_get_subscription_unauthenticated(self, client):
        """Test getting subscription without auth fails."""
        response = await client.get("/api/v1/billing/subscription")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_subscription_no_subscription(self, client, auth_token, test_user_org, db_session):
        """Test getting subscription when no subscription exists."""
        response = await client.get(
            "/api/v1/billing/subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["plan_code"] == "none"
        assert data["status"] == "inactive"

    @pytest.mark.asyncio
    async def test_get_subscription_with_active_plan(self, client, auth_token, test_user_org, billing_plans, db_session):
        """Test getting subscription when user has active subscription."""
        # Create subscription
        free_plan = next(p for p in billing_plans if p.code == BillingPlanCode.FREE)
        
        subscription = Subscription(
            organization_id=test_user_org["org"].id,
            plan_id=free_plan.id,
            status=SubscriptionStatus.ACTIVE,
        )
        db_session.add(subscription)
        await db_session.commit()
        
        response = await client.get(
            "/api/v1/billing/subscription",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["plan_code"] == "free"
        assert data["status"] == "active"


class TestBillingSubscribe:
    """Tests for POST /api/v1/billing/subscribe/{plan_code}."""

    @pytest.mark.skip(reason="Requires real Stripe credentials - integration test")
    @pytest.mark.asyncio
    async def test_subscribe_to_pro_plan(self, client, auth_token, test_user_org, billing_plans, db_session):
        """Test subscribing to pro plan."""
        response = await client.post(
            "/api/v1/billing/subscribe/pro",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "success_url": "https://pranely.com/success",
                "cancel_url": "https://pranely.com/cancel",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "checkout_url" in data
        assert "session_id" in data
        assert data["plan_code"] == "pro"

    @pytest.mark.asyncio
    async def test_subscribe_unauthenticated(self, client):
        """Test subscribing without auth fails."""
        response = await client.post(
            "/api/v1/billing/subscribe/pro",
            json={
                "success_url": "https://pranely.com/success",
                "cancel_url": "https://pranely.com/cancel",
            },
        )
        
        assert response.status_code == 401

    @pytest.mark.skip(reason="Requires real Stripe credentials - integration test")
    @pytest.mark.asyncio
    async def test_subscribe_invalid_plan(self, client, auth_token, db_session):
        """Test subscribing to invalid plan fails."""
        response = await client.post(
            "/api/v1/billing/subscribe/invalid_plan",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "success_url": "https://pranely.com/success",
                "cancel_url": "https://pranely.com/cancel",
            },
        )
        
        assert response.status_code == 400

    @pytest.mark.skip(reason="Requires real Stripe credentials - integration test")
    @pytest.mark.asyncio
    async def test_subscribe_free_plan(self, client, auth_token, test_user_org, billing_plans, db_session):
        """Test subscribing to free plan."""
        response = await client.post(
            "/api/v1/billing/subscribe/free",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "success_url": "https://pranely.com/success",
                "cancel_url": "https://pranely.com/cancel",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["plan_code"] == "free"

    @pytest.mark.skip(reason="Requires real Stripe credentials - integration test")
    @pytest.mark.asyncio
    async def test_subscribe_enterprise_plan(self, client, auth_token, test_user_org, billing_plans, db_session):
        """Test subscribing to enterprise plan."""
        response = await client.post(
            "/api/v1/billing/subscribe/enterprise",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "success_url": "https://pranely.com/success",
                "cancel_url": "https://pranely.com/cancel",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["plan_code"] == "enterprise"


class TestBillingMultiTenant:
    """Tests for multi-tenant isolation in billing."""

    @pytest.mark.asyncio
    async def test_subscription_isolation(self, client, test_user_org, billing_plans, db_session):
        """Test that users can only see their org's subscription."""
        # Create subscription for test org
        free_plan = next(p for p in billing_plans if p.code == BillingPlanCode.FREE)
        subscription = Subscription(
            organization_id=test_user_org["org"].id,
            plan_id=free_plan.id,
            status=SubscriptionStatus.ACTIVE,
        )
        db_session.add(subscription)
        await db_session.commit()
        
        # Get token
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user_org["user"].email,
                "password": "testpassword123",
            },
        )
        token = response.json()["token"]["access_token"]
        
        # Verify subscription
        response = await client.get(
            "/api/v1/billing/subscription",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["organization_id"] == test_user_org["org"].id

    @pytest.mark.asyncio
    async def test_plans_visible_to_all(self, client, test_user_org, billing_plans, db_session):
        """Test that billing plans are visible to all (no org-specific)."""
        # Get plans without auth (public endpoint)
        response = await client.get("/api/v1/billing/plans")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["plans"]) >= 3