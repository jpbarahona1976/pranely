"""
Tests for Waste Movement API endpoints (FASE 5B).

Tests cover:
- CRUD operations (create, read, update, archive)
- Multi-tenant isolation
- RBAC (viewer cannot mutate)
- Soft-delete behavior
- Immutable movement protection
- Stats endpoint
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User,
    Organization,
    Membership,
    WasteMovement,
    MovementStatus,
    UserRole,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def mock_audit():
    """Auto-mock record_audit_event to avoid DB session issues in tests."""
    with patch('app.api.v1.waste.record_audit_event', new_callable=AsyncMock) as mock:
        yield mock

@pytest.fixture
async def org(db: AsyncSession) -> Organization:
    """Create a test organization."""
    org = Organization(name="Test Org Waste")
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@pytest.fixture
async def other_org(db: AsyncSession) -> Organization:
    """Create a second test organization for cross-tenant tests."""
    org = Organization(name="Other Org Waste")
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@pytest.fixture
async def owner_user(db: AsyncSession, org: Organization) -> User:
    """Create a test user with owner role."""
    user = User(
        email="owner@waste.test",
        hashed_password="hashed",
        full_name="Owner User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    membership = Membership(
        user_id=user.id,
        organization_id=org.id,
        role=UserRole.OWNER,
    )
    db.add(membership)
    await db.commit()
    
    return user


@pytest.fixture
async def member_user(db: AsyncSession, org: Organization) -> User:
    """Create a test user with member role."""
    user = User(
        email="member@waste.test",
        hashed_password="hashed",
        full_name="Member User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    membership = Membership(
        user_id=user.id,
        organization_id=org.id,
        role=UserRole.MEMBER,
    )
    db.add(membership)
    await db.commit()
    
    return user


@pytest.fixture
async def viewer_user(db: AsyncSession, org: Organization) -> User:
    """Create a test user with viewer role."""
    user = User(
        email="viewer@waste.test",
        hashed_password="hashed",
        full_name="Viewer User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    membership = Membership(
        user_id=user.id,
        organization_id=org.id,
        role=UserRole.VIEWER,
    )
    db.add(membership)
    await db.commit()
    
    return user


@pytest.fixture
async def other_org_user(db: AsyncSession, other_org: Organization) -> User:
    """Create a test user in another organization."""
    user = User(
        email="other@waste.test",
        hashed_password="hashed",
        full_name="Other User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    membership = Membership(
        user_id=user.id,
        organization_id=other_org.id,
        role=UserRole.OWNER,
    )
    db.add(membership)
    await db.commit()
    
    return user


@pytest.fixture
async def waste_movement(db: AsyncSession, org: Organization) -> WasteMovement:
    """Create a test waste movement."""
    movement = WasteMovement(
        organization_id=org.id,
        manifest_number="MAN-001",
        movement_type="transport",
        quantity=100.0,
        unit="kg",
        date=datetime.now(timezone.utc),
        status=MovementStatus.PENDING,
        is_immutable=False,
    )
    db.add(movement)
    await db.commit()
    await db.refresh(movement)
    return movement


@pytest.fixture
async def archived_movement(db: AsyncSession, org: Organization) -> WasteMovement:
    """Create an archived waste movement."""
    movement = WasteMovement(
        organization_id=org.id,
        manifest_number="MAN-ARCHIVED",
        status=MovementStatus.PENDING,
        archived_at=datetime.now(timezone.utc),
    )
    db.add(movement)
    await db.commit()
    await db.refresh(movement)
    return movement


@pytest.fixture
async def immutable_movement(db: AsyncSession, org: Organization) -> WasteMovement:
    """Create an immutable waste movement."""
    movement = WasteMovement(
        organization_id=org.id,
        manifest_number="MAN-IMMUTABLE",
        status=MovementStatus.VALIDATED,
        is_immutable=True,
    )
    db.add(movement)
    await db.commit()
    await db.refresh(movement)
    return movement


# =============================================================================
# Helper functions
# =============================================================================

def create_test_token(user_id: int, org_id: int, role: str) -> str:
    """Create a test JWT token."""
    from app.core.tokens import create_access_token
    return create_access_token(
        user_id=user_id,
        org_id=org_id,
        role=role,
    )


# =============================================================================
# Test: Create Waste Movement
# =============================================================================

class TestCreateWasteMovement:
    """Tests for POST /api/v1/waste endpoint."""
    
    @pytest.mark.asyncio
    async def test_create_movement_success(
        self,
        client,
        db,
        owner_user,
        org,
    ):
        """Owner can create a waste movement."""
        token = create_test_token(owner_user.id, org.id, "owner")
        
        response = await client.post(
            "/api/v1/waste",
            json={
                "manifest_number": "MAN-NEW-001",
                "movement_type": "transport",
                "quantity": 150.0,
                "unit": "kg",
                "status": "pending",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["manifest_number"] == "MAN-NEW-001"
        assert data["movement_type"] == "transport"
        assert data["quantity"] == 150.0
        assert data["status"] == "pending"
        assert data["is_immutable"] is False
        assert data["archived_at"] is None
        assert data["organization_id"] == org.id
    
    @pytest.mark.asyncio
    async def test_create_movement_minimal(
        self,
        client,
        db,
        member_user,
        org,
    ):
        """Member can create a waste movement with minimal data."""
        token = create_test_token(member_user.id, org.id, "member")
        
        response = await client.post(
            "/api/v1/waste",
            json={
                "manifest_number": "MAN-MINIMAL",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["manifest_number"] == "MAN-MINIMAL"
        assert data["status"] == "pending"  # Default
    
    @pytest.mark.asyncio
    async def test_create_movement_unauthorized(
        self,
        client,
        db,
        viewer_user,
        org,
    ):
        """Viewer cannot create a waste movement."""
        token = create_test_token(viewer_user.id, org.id, "viewer")
        
        response = await client.post(
            "/api/v1/waste",
            json={
                "manifest_number": "MAN-FORBIDDEN",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Test: List Waste Movements
# =============================================================================

class TestListWasteMovements:
    """Tests for GET /api/v1/waste endpoint."""
    
    @pytest.mark.asyncio
    async def test_list_movements_empty(
        self,
        client,
        db,
        owner_user,
        org,
    ):
        """List returns empty when no movements exist."""
        token = create_test_token(owner_user.id, org.id, "owner")
        
        response = await client.get(
            "/api/v1/waste",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_list_movements_returns_tenant_only(
        self,
        client,
        db,
        owner_user,
        org,
        other_org_user,
        other_org,
        waste_movement,
    ):
        """List only returns movements from current tenant."""
        # Create movement in other org
        other_movement = WasteMovement(
            organization_id=other_org.id,
            manifest_number="OTHER-MAN",
            status=MovementStatus.PENDING,
        )
        db.add(other_movement)
        await db.commit()
        
        token = create_test_token(owner_user.id, org.id, "owner")
        
        response = await client.get(
            "/api/v1/waste",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["manifest_number"] == "MAN-001"
    
    @pytest.mark.asyncio
    async def test_list_excludes_archived_by_default(
        self,
        client,
        db,
        owner_user,
        org,
        archived_movement,
    ):
        """Archived movements are excluded from list by default."""
        token = create_test_token(owner_user.id, org.id, "owner")
        
        response = await client.get(
            "/api/v1/waste",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_list_includes_archived_when_requested(
        self,
        client,
        db,
        owner_user,
        org,
        archived_movement,
    ):
        """Archived movements are included with include_archived=true."""
        token = create_test_token(owner_user.id, org.id, "owner")
        
        response = await client.get(
            "/api/v1/waste?include_archived=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["manifest_number"] == "MAN-ARCHIVED"
    
    @pytest.mark.asyncio
    async def test_list_filter_by_status(
        self,
        client,
        db,
        owner_user,
        org,
    ):
        """List can filter by status."""
        # Create movements with different statuses
        for i, status_val in enumerate(["pending", "validated", "rejected"]):
            movement = WasteMovement(
                organization_id=org.id,
                manifest_number=f"MAN-{i}",
                status=MovementStatus(status_val),
            )
            db.add(movement)
        await db.commit()
        
        token = create_test_token(owner_user.id, org.id, "owner")
        
        response = await client.get(
            "/api/v1/waste?status_filter=validated",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "validated"


# =============================================================================
# Test: Get Waste Movement
# =============================================================================

class TestGetWasteMovement:
    """Tests for GET /api/v1/waste/{id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_movement_success(
        self,
        client,
        db,
        owner_user,
        org,
        waste_movement,
    ):
        """Get movement by ID returns correct data."""
        token = create_test_token(owner_user.id, org.id, "owner")
        
        response = await client.get(
            f"/api/v1/waste/{waste_movement.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == waste_movement.id
        assert data["manifest_number"] == "MAN-001"
    
    @pytest.mark.asyncio
    async def test_get_movement_not_found(
        self,
        client,
        db,
        owner_user,
        org,
    ):
        """Get non-existent movement returns 404."""
        token = create_test_token(owner_user.id, org.id, "owner")
        
        response = await client.get(
            "/api/v1/waste/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_get_movement_cross_tenant_denied(
        self,
        client,
        db,
        other_org_user,
        other_org,
        waste_movement,
    ):
        """Cannot get movement from different organization."""
        token = create_test_token(other_org_user.id, other_org.id, "owner")
        
        response = await client.get(
            f"/api/v1/waste/{waste_movement.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Test: Update Waste Movement
# =============================================================================

class TestUpdateWasteMovement:
    """Tests for PATCH /api/v1/waste/{id} endpoint."""
    
    @pytest.mark.asyncio
    async def test_update_movement_success(
        self,
        client,
        db,
        owner_user,
        org,
        waste_movement,
    ):
        """Owner can update a mutable movement."""
        token = create_test_token(owner_user.id, org.id, "owner")
        
        response = await client.patch(
            f"/api/v1/waste/{waste_movement.id}",
            json={
                "quantity": 200.0,
                "status": "in_review",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["quantity"] == 200.0
        assert data["status"] == "in_review"
    
    @pytest.mark.asyncio
    async def test_update_immutable_movement_rejected(
        self,
        client,
        db,
        owner_user,
        org,
        immutable_movement,
    ):
        """Cannot update an immutable movement."""
        token = create_test_token(owner_user.id, org.id, "owner")
        
        response = await client.patch(
            f"/api/v1/waste/{immutable_movement.id}",
            json={
                "quantity": 999.0,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_409_CONFLICT
        error_detail = response.json()["detail"]["detail"].lower()
        assert "validated" in error_detail or "immutable" in error_detail
    
    @pytest.mark.asyncio
    async def test_update_archived_movement_returns_404(
        self,
        client,
        db,
        owner_user,
        org,
        archived_movement,
    ):
        """Cannot update an archived movement - returns 404 (not found in default query)."""
        token = create_test_token(owner_user.id, org.id, "owner")
        
        # Archived movements are excluded from default queries
        # The update endpoint uses get_movement_or_404 which excludes archived by default
        response = await client.patch(
            f"/api/v1/waste/{archived_movement.id}",
            json={
                "quantity": 50.0,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        
        # Returns 404 because archived movements are filtered out
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Test: Archive Waste Movement
# =============================================================================

class TestArchiveWasteMovement:
    """Tests for POST /api/v1/waste/{id}/archive endpoint."""
    
    @pytest.mark.asyncio
    async def test_archive_movement_success(
        self,
        client,
        db,
        owner_user,
        org,
        waste_movement,
    ):
        """Owner can archive a waste movement."""
        token = create_test_token(owner_user.id, org.id, "owner")
        
        response = await client.post(
            f"/api/v1/waste/{waste_movement.id}/archive",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["archived_at"] is not None
        
        # Verify in DB
        await db.refresh(waste_movement)
        assert waste_movement.archived_at is not None
    
    @pytest.mark.asyncio
    async def test_archive_already_archived_rejected(
        self,
        client,
        db,
        owner_user,
        org,
        archived_movement,
    ):
        """Cannot archive an already archived movement."""
        token = create_test_token(owner_user.id, org.id, "owner")
        
        response = await client.post(
            f"/api/v1/waste/{archived_movement.id}/archive",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already archived" in response.json()["detail"]["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_archive_cross_tenant_denied(
        self,
        client,
        db,
        other_org_user,
        other_org,
        waste_movement,
    ):
        """Cannot archive movement from different organization."""
        token = create_test_token(other_org_user.id, other_org.id, "owner")
        
        response = await client.post(
            f"/api/v1/waste/{waste_movement.id}/archive",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Test: Stats Endpoint
# =============================================================================

class TestWasteStats:
    """Tests for GET /api/v1/waste/stats endpoint."""
    
    @pytest.mark.asyncio
    async def test_stats_empty(
        self,
        client,
        db,
        owner_user,
        org,
    ):
        """Stats returns zeros when no movements."""
        token = create_test_token(owner_user.id, org.id, "owner")
        
        response = await client.get(
            "/api/v1/waste/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["archived_count"] == 0
        assert "by_status" in data
    
    @pytest.mark.asyncio
    async def test_stats_returns_tenant_only(
        self,
        client,
        db,
        owner_user,
        org,
        other_org,
        other_org_user,
    ):
        """Stats only includes movements from current tenant."""
        # Create movements in both orgs
        for i, org_id in enumerate([org.id, other_org.id]):
            movement = WasteMovement(
                organization_id=org_id,
                manifest_number=f"MAN-{i}",
                status=MovementStatus.PENDING,
            )
            db.add(movement)
        await db.commit()
        
        token = create_test_token(owner_user.id, org.id, "owner")
        
        response = await client.get(
            "/api/v1/waste/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1  # Only org's movement
        assert data["by_status"]["pending"] == 1
    
    @pytest.mark.asyncio
    async def test_stats_counts_by_status(
        self,
        client,
        db,
        owner_user,
        org,
    ):
        """Stats correctly counts movements by status."""
        statuses = ["pending", "pending", "validated", "rejected", "exception"]
        for i, status_val in enumerate(statuses):
            movement = WasteMovement(
                organization_id=org.id,
                manifest_number=f"MAN-{i}",
                status=MovementStatus(status_val),
            )
            db.add(movement)
        await db.commit()
        
        token = create_test_token(owner_user.id, org.id, "owner")
        
        response = await client.get(
            "/api/v1/waste/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 5
        assert data["by_status"]["pending"] == 2
        assert data["by_status"]["validated"] == 1
        assert data["by_status"]["rejected"] == 1
        assert data["by_status"]["exception"] == 1


# =============================================================================
# Test: Cross-tenant Isolation
# =============================================================================

class TestWasteCrossTenantIsolation:
    """Tests for cross-tenant access control."""
    
    @pytest.mark.asyncio
    async def test_list_cross_tenant_denied(
        self,
        client,
        db,
        other_org_user,
        other_org,
        waste_movement,
    ):
        """Cannot list another org's movements."""
        token = create_test_token(other_org_user.id, other_org.id, "owner")
        
        response = await client.get(
            "/api/v1/waste",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0  # Other org has no movements
    
    @pytest.mark.asyncio
    async def test_update_cross_tenant_denied(
        self,
        client,
        db,
        other_org_user,
        other_org,
        waste_movement,
    ):
        """Cannot update another org's movement."""
        token = create_test_token(other_org_user.id, other_org.id, "owner")
        
        response = await client.patch(
            f"/api/v1/waste/{waste_movement.id}",
            json={"quantity": 999.0},
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Test: RBAC Enforcement
# =============================================================================

class TestWasteRBAC:
    """Tests for role-based access control."""
    
    @pytest.mark.asyncio
    async def test_member_can_create(
        self,
        client,
        db,
        member_user,
        org,
    ):
        """Member role can create movements."""
        token = create_test_token(member_user.id, org.id, "member")
        
        response = await client.post(
            "/api/v1/waste",
            json={"manifest_number": "MAN-MEMBER"},
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_201_CREATED
    
    @pytest.mark.asyncio
    async def test_viewer_cannot_create(
        self,
        client,
        db,
        viewer_user,
        org,
    ):
        """Viewer role cannot create movements."""
        token = create_test_token(viewer_user.id, org.id, "viewer")
        
        response = await client.post(
            "/api/v1/waste",
            json={"manifest_number": "MAN-VIEWER"},
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_viewer_can_read(
        self,
        client,
        db,
        viewer_user,
        org,
        waste_movement,
    ):
        """Viewer role can read movements."""
        token = create_test_token(viewer_user.id, org.id, "viewer")
        
        response = await client.get(
            f"/api/v1/waste/{waste_movement.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_viewer_cannot_update(
        self,
        client,
        db,
        viewer_user,
        org,
        waste_movement,
    ):
        """Viewer role cannot update movements."""
        token = create_test_token(viewer_user.id, org.id, "viewer")
        
        response = await client.patch(
            f"/api/v1/waste/{waste_movement.id}",
            json={"quantity": 999.0},
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    @pytest.mark.asyncio
    async def test_viewer_cannot_archive(
        self,
        client,
        db,
        viewer_user,
        org,
        waste_movement,
    ):
        """Viewer role cannot archive movements."""
        token = create_test_token(viewer_user.id, org.id, "viewer")
        
        response = await client.post(
            f"/api/v1/waste/{waste_movement.id}/archive",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
