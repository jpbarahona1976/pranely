"""Tests for Command Center API - 8B Phase FIX PACK.

FIX 8B Issues:
1. Feature Flags persistence (now in Organization.extra_data)
2. Director role added (full access)
3. Member role is read-only (GET allowed, mutations denied)
"""
import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime

from app.main import app
from app.core.database import get_db, engine
from app.models import (
    Base, Organization, User, Membership, UserRole,
    AuditLog, AuditLogResult, Subscription, BillingPlan, BillingPlanCode, UsageCycle,
)
from app.core.security import hash_password


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
async def db_session():
    """Create a test database session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    from sqlalchemy.ext.asyncio import AsyncSession
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_org(db_session):
    """Create test organization."""
    org = Organization(name="Test Org", is_active=True)
    db_session.add(org)
    await db_session.flush()
    return org


@pytest.fixture
async def owner_user(db_session, test_org):
    """Create owner user."""
    user = User(
        email="owner@test.com",
        hashed_password=hash_password("password123"),
        full_name="Owner User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = Membership(
        user_id=user.id,
        organization_id=test_org.id,
        role=UserRole.OWNER,
    )
    db_session.add(membership)
    await db_session.flush()
    return user


@pytest.fixture
async def admin_user(db_session, test_org):
    """Create admin user."""
    user = User(
        email="admin@test.com",
        hashed_password=hash_password("password123"),
        full_name="Admin User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = Membership(
        user_id=user.id,
        organization_id=test_org.id,
        role=UserRole.ADMIN,
    )
    db_session.add(membership)
    await db_session.flush()
    return user


@pytest.fixture
async def member_user(db_session, test_org):
    """Create member user."""
    user = User(
        email="member@test.com",
        hashed_password=hash_password("password123"),
        full_name="Member User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = Membership(
        user_id=user.id,
        organization_id=test_org.id,
        role=UserRole.MEMBER,
    )
    db_session.add(membership)
    await db_session.flush()
    return user


# FIX 8B: New Director fixture
@pytest.fixture
async def director_user(db_session, test_org):
    """Create director user - FIX 8B."""
    user = User(
        email="director@test.com",
        hashed_password=hash_password("password123"),
        full_name="Director User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = Membership(
        user_id=user.id,
        organization_id=test_org.id,
        role=UserRole.DIRECTOR,
    )
    db_session.add(membership)
    await db_session.flush()
    return user


@pytest.fixture
async def viewer_user(db_session, test_org):
    """Create viewer user - still denied access."""
    user = User(
        email="viewer@test.com",
        hashed_password=hash_password("password123"),
        full_name="Viewer User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = Membership(
        user_id=user.id,
        organization_id=test_org.id,
        role=UserRole.VIEWER,
    )
    db_session.add(membership)
    await db_session.flush()
    return user


@pytest.fixture
async def second_org(db_session):
    """Create second organization for cross-tenant tests."""
    org = Organization(name="Second Org", is_active=True)
    db_session.add(org)
    await db_session.flush()
    return org


def get_token(user_id: int, org_id: int, role: str) -> str:
    """Generate test JWT token."""
    from app.core.tokens import create_access_token
    return create_access_token(
        user_id=user_id,
        org_id=org_id,
        role=role,
        permissions=["read", "manage_operators", "change_config", "view_quotas", "toggle_features", "view_audit"],
    )


# =============================================================================
# RBAC TESTS - FIX 8B
# =============================================================================

class TestRBACCommandCenter:
    """Test RBAC for Command Center - FIX 8B."""
    
    @pytest.mark.asyncio
    async def test_owner_can_access(self, owner_user, test_org):
        """Owner role can access all command center endpoints."""
        token = get_token(owner_user.id, test_org.id, "owner")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/command/operators",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_admin_can_access(self, admin_user, test_org):
        """Admin role can access command center."""
        token = get_token(admin_user.id, test_org.id, "admin")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/command/operators",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_director_can_access(self, director_user, test_org):
        """FIX 8B: Director role can access command center - FULL ACCESS."""
        token = get_token(director_user.id, test_org.id, "director")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test GET (should work)
            response = await client.get(
                "/api/v1/command/operators",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            
            # Test PATCH (should also work for director)
            response = await client.patch(
                "/api/v1/command/features/mobile_bridge",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"enabled": False},
            )
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_member_can_read_but_not_mutate(self, member_user, test_org):
        """FIX 8B: Member role can READ but cannot MUTATE Command Center."""
        token = get_token(member_user.id, test_org.id, "member")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # FIX 8B: GET should work for member
            response = await client.get(
                "/api/v1/command/operators",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            
            response = await client.get(
                "/api/v1/command/features",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            
            response = await client.get(
                "/api/v1/command/config",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            
            # FIX 8B: Mutations should be denied for member
            response = await client.post(
                "/api/v1/command/operators/invite",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"email": "new@test.com", "role": "member"},
            )
            assert response.status_code == 403
            assert "read-only" in response.json()["detail"]["detail"].lower() or "write access" in response.json()["detail"]["detail"].lower()
            
            response = await client.patch(
                "/api/v1/command/config",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"name": "New Name"},
            )
            assert response.status_code == 403
            
            response = await client.patch(
                "/api/v1/command/features/mobile_bridge",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"enabled": False},
            )
            assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_viewer_is_denied(self, viewer_user, test_org):
        """Viewer role is denied access completely."""
        token = get_token(viewer_user.id, test_org.id, "viewer")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/command/operators",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 403


# =============================================================================
# FEATURE FLAGS PERSISTENCE TEST - FIX 8B
# =============================================================================

class TestFeatureFlagsPersistence:
    """Test that feature flags persist in DB - FIX 8B."""
    
    @pytest.mark.asyncio
    async def test_flags_persist_after_toggle(self, owner_user, test_org, db_session):
        """FIX 8B: Flags persist in org.extra_data, survive across requests."""
        token = get_token(owner_user.id, test_org.id, "owner")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Toggle a flag
            response = await client.patch(
                "/api/v1/command/features/mobile_bridge",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"enabled": False},
            )
            assert response.status_code == 200
            
            # Verify it's persisted in DB
            await db_session.refresh(test_org)
            flags = test_org.extra_data.get("feature_flags", []) if test_org.extra_data else []
            mobile_bridge = next((f for f in flags if f["key"] == "mobile_bridge"), None)
            assert mobile_bridge is not None
            assert mobile_bridge["enabled"] is False
    
    @pytest.mark.asyncio
    async def test_flags_persist_across_sessions(self, owner_user, test_org, db_session):
        """FIX 8B: Verify flags persist across different sessions/requests."""
        token = get_token(owner_user.id, test_org.id, "owner")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Set initial state
            await client.patch(
                "/api/v1/command/features/ai_extraction",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"enabled": False},
            )
            
            # Commit to DB
            await db_session.commit()
        
        # Re-fetch org from DB (simulate new session)
        from sqlalchemy import select
        result = await db_session.execute(
            select(Organization).where(Organization.id == test_org.id)
        )
        org = result.scalar_one()
        
        flags = org.extra_data.get("feature_flags", []) if org.extra_data else []
        ai_extraction = next((f for f in flags if f["key"] == "ai_extraction"), None)
        
        assert ai_extraction is not None
        assert ai_extraction["enabled"] is False
    
    @pytest.mark.asyncio
    async def test_flags_default_when_no_extra_data(self, owner_user, test_org, db_session):
        """FIX 8B: Defaults are used when org has no extra_data."""
        # Ensure org has no extra_data
        test_org.extra_data = None
        await db_session.commit()
        
        token = get_token(owner_user.id, test_org.id, "owner")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/command/features",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data = response.json()
            
            # Should return default flags
            assert data["total"] == 5
            keys = [f["key"] for f in data["flags"]]
            assert "mobile_bridge" in keys
            assert "ai_extraction" in keys


# =============================================================================
# DIRECTOR ROLE FUNCTIONAL TESTS
# =============================================================================

class TestDirectorRole:
    """Test Director role has full access - FIX 8B."""
    
    @pytest.mark.asyncio
    async def test_director_can_invite_operator(self, director_user, test_org, db_session):
        """Director can invite operators."""
        token = get_token(director_user.id, test_org.id, "director")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/command/operators/invite",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"email": "invited@test.com", "role": "member"},
            )
            assert response.status_code == 201
            assert response.json()["operator"]["role"] == "member"
    
    @pytest.mark.asyncio
    async def test_director_can_update_config(self, director_user, test_org):
        """Director can update tenant configuration."""
        token = get_token(director_user.id, test_org.id, "director")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.patch(
                "/api/v1/command/config",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"name": "Director Updated Org"},
            )
            assert response.status_code == 200
            assert response.json()["config"]["name"] == "Director Updated Org"
    
    @pytest.mark.asyncio
    async def test_director_can_toggle_features(self, director_user, test_org):
        """Director can toggle feature flags."""
        token = get_token(director_user.id, test_org.id, "director")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.patch(
                "/api/v1/command/features/advanced_export",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"enabled": True},
            )
            assert response.status_code == 200
            assert response.json()["flag"]["enabled"] is True
    
    @pytest.mark.asyncio
    async def test_director_can_view_all(self, director_user, test_org):
        """Director can view all Command Center data."""
        token = get_token(director_user.id, test_org.id, "director")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # All GET endpoints
            for endpoint in ["/operators", "/config", "/quotas", "/features", "/audit", "/stats"]:
                response = await client.get(
                    f"/api/v1/command{endpoint}",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert response.status_code == 200, f"GET {endpoint} should work for director"


# =============================================================================
# MULTI-TENANT ISOLATION TESTS
# =============================================================================

class TestTenantIsolation:
    """Test organization isolation."""
    
    @pytest.mark.asyncio
    async def test_org_flags_isolated(self, owner_user, test_org, second_org, db_session):
        """Each org has its own feature flags - FIX 8B."""
        token = get_token(owner_user.id, test_org.id, "owner")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Toggle flag for org1
            response = await client.patch(
                "/api/v1/command/features/mobile_bridge",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"enabled": False},
            )
            assert response.status_code == 200
        
        # Create user in org2
        from sqlalchemy import select
        user2 = User(
            email="user2@test.com",
            hashed_password=hash_password("password123"),
            is_active=True,
        )
        db_session.add(user2)
        await db_session.flush()
        
        membership2 = Membership(
            user_id=user2.id,
            organization_id=second_org.id,
            role=UserRole.OWNER,
        )
        db_session.add(membership2)
        await db_session.commit()
        
        token2 = get_token(user2.id, second_org.id, "owner")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Org2 should have default (enabled: True)
            response = await client.get(
                "/api/v1/command/features",
                headers={"Authorization": f"Bearer {token2}"},
            )
            assert response.status_code == 200
            data = response.json()
            
            mobile_bridge = next((f for f in data["flags"] if f["key"] == "mobile_bridge"), None)
            assert mobile_bridge is not None
            assert mobile_bridge["enabled"] is True  # Default, not org1's False


# =============================================================================
# AUDIT LOG TESTS
# =============================================================================

class TestAuditLogs:
    """Test audit logging still works correctly."""
    
    @pytest.mark.asyncio
    async def test_feature_toggle_creates_audit_log(self, director_user, test_org, db_session):
        """Feature toggles create audit logs."""
        token = get_token(director_user.id, test_org.id, "director")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.patch(
                "/api/v1/command/features/legal_radar",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"enabled": False},
            )
        
        # Verify audit log
        from sqlalchemy import select
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.organization_id == test_org.id,
                AuditLog.action == "feature.toggled",
            ).order_by(AuditLog.timestamp.desc())
        )
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.user_id == director_user.id


# =============================================================================
# EXISTING TESTS (unchanged)
# =============================================================================

class TestOperatorsEndpoint:
    """Test operators CRUD operations - existing tests."""
    
    @pytest.mark.asyncio
    async def test_list_operators(self, owner_user, test_org):
        """List operators returns all members."""
        token = get_token(owner_user.id, test_org.id, "owner")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/command/operators",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["total"] >= 1


class TestConfigEndpoint:
    """Test configuration endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_config(self, owner_user, test_org):
        """Get tenant configuration."""
        token = get_token(owner_user.id, test_org.id, "owner")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/command/config",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["organization_id"] == test_org.id


class TestStatsEndpoint:
    """Test statistics endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_stats(self, owner_user, test_org):
        """Get command center statistics."""
        token = get_token(owner_user.id, test_org.id, "owner")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/command/stats",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "total_operators" in data
            assert "current_plan" in data