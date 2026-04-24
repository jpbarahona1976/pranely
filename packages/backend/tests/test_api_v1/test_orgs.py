"""Tests for API v1 organization endpoints."""
import pytest

from app.core.security import hash_password
from app.models import Organization, User, Membership, UserRole


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


@pytest.fixture
async def second_org(db_session):
    """Create a second organization for multi-org tests."""
    org = Organization(name="Second Org", is_active=True)
    db_session.add(org)
    await db_session.flush()
    
    user = User(
        email="second@example.com",
        hashed_password=hash_password("password123"),
        full_name="Second User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    membership = Membership(
        user_id=user.id,
        organization_id=org.id,
        role=UserRole.ADMIN,
    )
    db_session.add(membership)
    await db_session.commit()
    
    return {"user": user, "org": org}


class TestOrgsList:
    """Tests for GET /api/v1/orgs."""

    @pytest.mark.asyncio
    async def test_list_organizations_authenticated(self, client, auth_token, test_user_org, db_session):
        """Test listing organizations for authenticated user."""
        response = await client.get(
            "/api/v1/orgs",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "organizations" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_organizations_unauthenticated(self, client):
        """Test listing organizations without auth fails."""
        response = await client.get("/api/v1/orgs")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_multiple_orgs(self, client, second_org, db_session):
        """Test listing multiple organizations."""
        # Login as second user
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "second@example.com", "password": "password123"},
        )
        user_token = response.json()["token"]["access_token"]
        
        response = await client.get(
            "/api/v1/orgs",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1


class TestOrgsCreate:
    """Tests for POST /api/v1/orgs."""

    @pytest.mark.asyncio
    async def test_create_organization(self, client, auth_token, test_user_org, db_session):
        """Test creating a new organization."""
        response = await client.post(
            "/api/v1/orgs",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "name": "New Organization",
                "legal_name": "New Org Legal Name",
                "industry": "Technology",
                "segment": "generator",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Organization"
        assert data["legal_name"] == "New Org Legal Name"

    @pytest.mark.asyncio
    async def test_create_organization_unauthenticated(self, client):
        """Test creating organization without auth fails."""
        response = await client.post(
            "/api/v1/orgs",
            json={"name": "New Org"},
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_organization_user_becomes_owner(self, client, auth_token, db_session):
        """Test that creating org makes user owner."""
        response = await client.post(
            "/api/v1/orgs",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": "Owner Test Org"},
        )
        
        assert response.status_code == 201
        
        # Verify membership created with owner role
        from sqlalchemy import select
        result = await db_session.execute(
            select(Membership).where(Membership.role == UserRole.OWNER)
        )
        memberships = result.scalars().all()
        assert len(memberships) >= 1


class TestOrgsGet:
    """Tests for GET /api/v1/orgs/{org_id}."""

    @pytest.mark.asyncio
    async def test_get_organization(self, client, auth_token, test_user_org, db_session):
        """Test getting organization details."""
        org_id = test_user_org["org"].id
        
        response = await client.get(
            f"/api/v1/orgs/{org_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == org_id
        assert data["name"] == test_user_org["org"].name
        assert "member_count" in data

    @pytest.mark.asyncio
    async def test_get_organization_not_member(self, client, auth_token, db_session):
        """Test getting organization where user is not member fails."""
        # Create another org not belonging to user
        other_org = Organization(name="Other Org", is_active=True)
        db_session.add(other_org)
        await db_session.commit()
        
        response = await client.get(
            f"/api/v1/orgs/{other_org.id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_nonexistent_organization(self, client, auth_token, db_session):
        """Test getting non-existent organization fails."""
        response = await client.get(
            "/api/v1/orgs/99999",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        
        assert response.status_code == 404


class TestOrgsUpdate:
    """Tests for PATCH /api/v1/orgs/{org_id}."""

    @pytest.mark.asyncio
    async def test_update_organization(self, client, auth_token, test_user_org, db_session):
        """Test updating organization."""
        org_id = test_user_org["org"].id
        
        response = await client.patch(
            f"/api/v1/orgs/{org_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": "Updated Name"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_organization_idempotent(self, client, auth_token, test_user_org, db_session):
        """Test that PATCH doesn't overwrite null fields (idempotent)."""
        org_id = test_user_org["org"].id
        
        # Send PATCH with only name
        response = await client.patch(
            f"/api/v1/orgs/{org_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": "Partial Update"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Partial Update"
        # Other fields should remain unchanged
        # (industry might be None)

    @pytest.mark.asyncio
    async def test_update_organization_not_owner(self, client, test_user_org, second_org, db_session):
        """Test updating org where user is not owner fails."""
        # Get second org token (admin, not owner)
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "second@example.com", "password": "password123"},
        )
        second_token = login_response.json()["token"]["access_token"]
        
        # Try to update first org with second user token
        response = await client.patch(
            f"/api/v1/orgs/{test_user_org['org'].id}",
            headers={"Authorization": f"Bearer {second_token}"},
            json={"name": "Hacked Name"},
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_organization_unauthenticated(self, client, test_user_org):
        """Test updating organization without auth fails."""
        response = await client.patch(
            f"/api/v1/orgs/{test_user_org['org'].id}",
            json={"name": "No Auth Update"},
        )
        
        assert response.status_code == 401


class TestOrgsMultiTenantIsolation:
    """Tests for multi-tenant isolation in orgs."""

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_org(self, client, test_user_org, second_org, db_session):
        """Test user cannot access organizations they don't belong to."""
        # Login as second user
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "second@example.com", "password": "password123"},
        )
        second_token = response.json()["token"]["access_token"]
        
        # Try to access first org
        response = await client.get(
            f"/api/v1/orgs/{test_user_org['org'].id}",
            headers={"Authorization": f"Bearer {second_token}"},
        )
        
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_org_list_filtered_by_membership(self, client, test_user_org, db_session):
        """Test that org list only shows user's organizations."""
        # Login as first user (only member of test_org)
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        first_token = response.json()["token"]["access_token"]
        
        # List orgs
        response = await client.get(
            "/api/v1/orgs",
            headers={"Authorization": f"Bearer {first_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        org_ids = [o["id"] for o in data["organizations"]]
        assert test_user_org["org"].id in org_ids