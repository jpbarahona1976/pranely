"""Full tests for waste API endpoints.

FASE 9A.1 FIX: Complete waste endpoint coverage.
"""
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone

from app.core.security import hash_password
from app.models import (
    Organization, User, Membership, UserRole,
    WasteMovement, MovementStatus, BillingPlan, BillingPlanCode,
    Subscription, SubscriptionStatus, UsageCycle
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def waste_owner(db_session):
    """Create owner user for waste tests."""
    org = Organization(name="Waste Test Org", is_active=True)
    db_session.add(org)
    await db_session.flush()
    
    user = User(
        email="waste_owner@test.com",
        hashed_password=hash_password("test123"),
        full_name="Waste Owner",
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
async def waste_member(db_session):
    """Create member user for waste tests."""
    org = Organization(name="Waste Test Org", is_active=True)
    db_session.add(org)
    await db_session.flush()
    
    user = User(
        email="waste_member@test.com",
        hashed_password=hash_password("test123"),
        full_name="Waste Member",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = Membership(
        user_id=user.id,
        organization_id=org.id,
        role=UserRole.MEMBER,
    )
    db_session.add(membership)
    await db_session.commit()
    
    return {"user": user, "org": org, "membership": membership}


@pytest.fixture
async def waste_viewer(db_session):
    """Create viewer user for waste tests."""
    org = Organization(name="Waste Test Org", is_active=True)
    db_session.add(org)
    await db_session.flush()
    
    user = User(
        email="waste_viewer@test.com",
        hashed_password=hash_password("test123"),
        full_name="Waste Viewer",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = Membership(
        user_id=user.id,
        organization_id=org.id,
        role=UserRole.VIEWER,
    )
    db_session.add(membership)
    await db_session.commit()
    
    return {"user": user, "org": org, "membership": membership}


@pytest.fixture
async def waste_movement(db_session, waste_owner):
    """Create a waste movement for testing."""
    movement = WasteMovement(
        organization_id=waste_owner["org"].id,
        manifest_number="MAN-TEST-001",
        movement_type="generation",
        quantity=100.5,
        unit="kg",
        status=MovementStatus.PENDING,
        is_immutable=False,
    )
    db_session.add(movement)
    await db_session.commit()
    await db_session.refresh(movement)
    return movement


@pytest.fixture
async def waste_movement_immutable(db_session, waste_owner):
    """Create an immutable waste movement."""
    movement = WasteMovement(
        organization_id=waste_owner["org"].id,
        manifest_number="MAN-IMMUTABLE-001",
        movement_type="generation",
        status=MovementStatus.VALIDATED,
        is_immutable=True,
    )
    db_session.add(movement)
    await db_session.commit()
    await db_session.refresh(movement)
    return movement


@pytest.fixture
async def waste_quota_available(db_session, waste_owner):
    """Create subscription with quota available."""
    # Create plan
    plan = BillingPlan(
        code=BillingPlanCode.PRO,
        name="Pro Plan",
        price_usd_cents=2999,
        doc_limit=1000,
        doc_limit_period="monthly",
        is_active=True,
    )
    db_session.add(plan)
    await db_session.flush()
    
    # Create subscription
    sub = Subscription(
        organization_id=waste_owner["org"].id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
    )
    db_session.add(sub)
    await db_session.flush()
    
    # Create usage cycle
    current_month = datetime.utcnow().strftime("%Y-%m")
    usage = UsageCycle(
        subscription_id=sub.id,
        month_year=current_month,
        docs_used=50,
        docs_limit=1000,
        is_locked=False,
    )
    db_session.add(usage)
    await db_session.commit()
    
    return {"subscription": sub, "usage": usage}


# =============================================================================
# Helper
# =============================================================================

async def get_token(client, email: str, password: str = "test123"):
    """Get auth token for user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    return response.json()["token"]["access_token"]


# =============================================================================
# Tests: Immutable Movement Protection
# =============================================================================

class TestWasteImmutableProtection:
    """Tests for immutable movement protection."""

    @pytest.mark.asyncio
    async def test_waste_update_immutable_reject_403(
        self, client, waste_owner, waste_movement_immutable, waste_quota_available, db_session
    ):
        """Test updating immutable movement returns 409 (not 403)."""
        token = await get_token(client, "waste_owner@test.com")
        
        response = await client.patch(
            f"/api/v1/waste/{waste_movement_immutable.id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"quantity": 200},
        )
        
        # Should return 409 Conflict, not 403
        assert response.status_code == 409
        data = response.json()
        # Message mentions "validated" and "cannot be modified"
        assert "validated" in data["detail"]["detail"].lower() or "cannot" in data["detail"]["detail"].lower()

    @pytest.mark.asyncio
    async def test_waste_archive_immutable_allowed(
        self, client, waste_owner, waste_movement_immutable, waste_quota_available, db_session
    ):
        """Test archiving immutable movement is allowed."""
        token = await get_token(client, "waste_owner@test.com")
        
        response = await client.post(
            f"/api/v1/waste/{waste_movement_immutable.id}/archive",
            headers={"Authorization": f"Bearer {token}"},
            json={},
        )
        
        assert response.status_code == 200


class TestWasteArchiveProtection:
    """Tests for double archive protection."""

    @pytest.mark.asyncio
    async def test_waste_archive_double_prevent(
        self, client, waste_owner, waste_movement, waste_quota_available, db_session
    ):
        """Test archiving already archived movement returns 400."""
        token = await get_token(client, "waste_owner@test.com")
        
        # First archive - should succeed
        response1 = await client.post(
            f"/api/v1/waste/{waste_movement.id}/archive",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response1.status_code == 200
        
        # Second archive - should fail with 400
        response2 = await client.post(
            f"/api/v1/waste/{waste_movement.id}/archive",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response2.status_code == 400
        assert "archived" in response2.json()["detail"]["detail"].lower()


# =============================================================================
# Tests: List, Pagination, Search
# =============================================================================

class TestWasteListPagination:
    """Tests for waste list pagination."""

    @pytest.mark.asyncio
    async def test_waste_list_pagination(
        self, client, waste_owner, waste_quota_available, db_session
    ):
        """Test waste list pagination returns correct structure."""
        token = await get_token(client, "waste_owner@test.com")
        
        # Create multiple movements
        for i in range(15):
            movement = WasteMovement(
                organization_id=waste_owner["org"].id,
                manifest_number=f"MAN-PAG-{i:03d}",
                status=MovementStatus.PENDING,
            )
            db_session.add(movement)
        await db_session.commit()
        
        # Get page 1
        response = await client.get(
            "/api/v1/waste?page=1&page_size=10",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data
        assert len(data["items"]) == 10
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_waste_list_page_2(
        self, client, waste_owner, waste_quota_available, db_session
    ):
        """Test getting page 2 of waste list."""
        token = await get_token(client, "waste_owner@test.com")
        
        # Create 15 movements
        for i in range(15):
            movement = WasteMovement(
                organization_id=waste_owner["org"].id,
                manifest_number=f"MAN-PAGE2-{i:03d}",
                status=MovementStatus.PENDING,
            )
            db_session.add(movement)
        await db_session.commit()
        
        response = await client.get(
            "/api/v1/waste?page=2&page_size=10",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert len(data["items"]) == 5  # Remaining items


class TestWasteSearchFilter:
    """Tests for waste search and filters."""

    @pytest.mark.asyncio
    async def test_waste_search_filter_manifest(
        self, client, waste_owner, waste_quota_available, db_session
    ):
        """Test searching by manifest number."""
        token = await get_token(client, "waste_owner@test.com")
        
        # Create movements with specific manifest numbers
        movements = [
            WasteMovement(
                organization_id=waste_owner["org"].id,
                manifest_number="MAN-UNIQUE-001",
                status=MovementStatus.PENDING,
            ),
            WasteMovement(
                organization_id=waste_owner["org"].id,
                manifest_number="MAN-UNIQUE-002",
                status=MovementStatus.PENDING,
            ),
            WasteMovement(
                organization_id=waste_owner["org"].id,
                manifest_number="OTHER-001",
                status=MovementStatus.PENDING,
            ),
        ]
        for m in movements:
            db_session.add(m)
        await db_session.commit()
        
        # Search for MAN-UNIQUE
        response = await client.get(
            "/api/v1/waste?search=MAN-UNIQUE",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should find 2 matching MAN-UNIQUE
        manifest_numbers = [m["manifest_number"] for m in data["items"]]
        assert all("MAN-UNIQUE" in mn for mn in manifest_numbers)

    @pytest.mark.asyncio
    async def test_waste_filter_by_status(
        self, client, waste_owner, waste_quota_available, db_session
    ):
        """Test filtering by status."""
        token = await get_token(client, "waste_owner@test.com")
        
        # Create movements with different statuses
        statuses = [MovementStatus.PENDING, MovementStatus.VALIDATED, MovementStatus.REJECTED]
        for i, status in enumerate(statuses):
            movement = WasteMovement(
                organization_id=waste_owner["org"].id,
                manifest_number=f"MAN-STATUS-{i}",
                status=status,
            )
            db_session.add(movement)
        await db_session.commit()
        
        # Filter by pending
        response = await client.get(
            "/api/v1/waste?status_filter=pending",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "pending"


class TestWasteMultiTenantIsolation:
    """Tests for multi-tenant isolation in waste."""

    @pytest.mark.asyncio
    async def test_org_cannot_see_other_org_waste(
        self, client, waste_owner, db_session
    ):
        """Test organization cannot see waste from other org."""
        # Create waste in waste_owner org
        movement = WasteMovement(
            organization_id=waste_owner["org"].id,
            manifest_number="MAN-PRIVATE-001",
            status=MovementStatus.PENDING,
        )
        db_session.add(movement)
        
        # Create another org
        org2 = Organization(name="Other Org", is_active=True)
        db_session.add(org2)
        await db_session.flush()
        
        user2 = User(
            email="other@test.com",
            hashed_password=hash_password("test123"),
            full_name="Other User",
            is_active=True,
        )
        db_session.add(user2)
        await db_session.flush()
        
        membership2 = Membership(
            user_id=user2.id,
            organization_id=org2.id,
            role=UserRole.OWNER,
        )
        db_session.add(membership2)
        await db_session.commit()
        
        # Get token for org2 user
        token2 = await get_token(client, "other@test.com")
        
        # Try to access waste from org1
        response = await client.get(
            "/api/v1/waste",
            headers={"Authorization": f"Bearer {token2}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should not contain MAN-PRIVATE-001
        manifest_numbers = [m["manifest_number"] for m in data["items"]]
        assert "MAN-PRIVATE-001" not in manifest_numbers


# =============================================================================
# Tests: RBAC for Waste
# =============================================================================

class TestWasteRBACRoles:
    """Tests for RBAC role enforcement in waste."""

    @pytest.mark.asyncio
    async def test_viewer_cannot_create_waste(
        self, client, waste_viewer, waste_quota_available, db_session
    ):
        """Test viewer role cannot create waste movements."""
        token = await get_token(client, "waste_viewer@test.com")
        
        response = await client.post(
            "/api/v1/waste",
            headers={"Authorization": f"Bearer {token}"},
            json={"manifest_number": "MAN-VIEWER-001"},
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_can_read_waste(
        self, client, waste_owner, waste_viewer, waste_movement, waste_quota_available, db_session
    ):
        """Test viewer role can read waste movements."""
        token = await get_token(client, "waste_viewer@test.com")
        
        response = await client.get(
            f"/api/v1/waste/{waste_movement.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_member_can_create_waste(
        self, client, waste_member, waste_quota_available, db_session
    ):
        """Test member role can create waste movements."""
        token = await get_token(client, "waste_member@test.com")
        
        with patch("app.api.v1.waste.record_audit_event", new_callable=AsyncMock):
            response = await client.post(
                "/api/v1/waste",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "manifest_number": "MAN-MEMBER-001",
                    "movement_type": "generation",
                },
            )
        
        assert response.status_code == 201