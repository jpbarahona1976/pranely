"""Tests for multi-org login with org selection (FIX 3)."""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import get_db, async_session_maker
from app.core.security import hash_password
from app.models import User, Organization, Membership, UserRole, Base


@pytest.fixture
async def multi_org_user(db_session):
    """Create a user with memberships in multiple organizations."""
    # Create user
    user = User(
        email="multi@test.com",
        hashed_password=hash_password("TestPass123!"),
        full_name="Multi Org User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    # Create organizations
    org1 = Organization(name="Acme Corp", is_active=True)
    org2 = Organization(name="Beta Inc", is_active=True)
    db_session.add_all([org1, org2])
    await db_session.flush()

    # Create memberships
    m1 = Membership(user_id=user.id, organization_id=org1.id, role=UserRole.OWNER)
    m2 = Membership(user_id=user.id, organization_id=org2.id, role=UserRole.MEMBER)
    db_session.add_all([m1, m2])
    await db_session.commit()

    return {
        "user": user,
        "org1": org1,
        "org2": org2,
    }


class TestLoginOrgSelection:
    """Test cases for multi-org login with org selection."""

    @pytest.mark.asyncio
    async def test_login_single_org_returns_token_directly(
        self, async_client: AsyncClient, test_user, test_org
    ):
        """When user has single org, token is returned directly."""
        response = await async_client.post(
            "/api/auth/login",
            json={"email": "test@test.com", "password": "testpass123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["token"] is not None
        assert data["token"]["access_token"] is not None
        assert data["organization"]["id"] == test_org.id

    @pytest.mark.asyncio
    async def test_login_multi_org_without_org_id_returns_orgs_list(
        self, async_client: AsyncClient, multi_org_user
    ):
        """When user has multiple orgs and no org_id param, return list."""
        response = await async_client.post(
            "/api/auth/login",
            json={"email": "multi@test.com", "password": "TestPass123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["token"] is None  # No token yet
        assert data["available_orgs"] is not None
        assert len(data["available_orgs"]) == 2
        assert data["message"] is not None

    @pytest.mark.asyncio
    async def test_login_multi_org_with_valid_org_id_returns_token(
        self, async_client: AsyncClient, multi_org_user
    ):
        """When org_id is provided and valid, return token for that org."""
        org2 = multi_org_user["org2"]

        response = await async_client.post(
            f"/api/auth/login?org_id={org2.id}",
            json={"email": "multi@test.com", "password": "TestPass123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["token"] is not None
        assert data["organization"]["id"] == org2.id

    @pytest.mark.asyncio
    async def test_login_multi_org_with_invalid_org_id_returns_403(
        self, async_client: AsyncClient, multi_org_user
    ):
        """When org_id is provided but user not member, return 403."""
        response = await async_client.post(
            "/api/auth/login?org_id=99999",
            json={"email": "multi@test.com", "password": "TestPass123!"},
        )

        assert response.status_code == 403
        data = response.json()
        assert "not a member" in data["detail"]["detail"]

    @pytest.mark.asyncio
    async def test_login_invalid_credentials_returns_401(
        self, async_client: AsyncClient
    ):
        """Invalid credentials return 401."""
        response = await async_client.post(
            "/api/auth/login",
            json={"email": "nonexistent@test.com", "password": "wrongpass"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user_returns_403(
        self, async_client: AsyncClient, db_session
    ):
        """Inactive user returns 403."""
        from sqlalchemy import update
        
        # Create inactive user
        user = User(
            email="inactive@test.com",
            hashed_password=hash_password("TestPass123!"),
            full_name="Inactive User",
            is_active=False,
        )
        db_session.add(user)
        await db_session.commit()

        response = await async_client.post(
            "/api/auth/login",
            json={"email": "inactive@test.com", "password": "TestPass123!"},
        )

        assert response.status_code == 403
