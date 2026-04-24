"""Tests for API v1 authentication endpoints."""
import pytest

from app.core.security import hash_password
from app.models import Organization, User, Membership, UserRole


@pytest.fixture
async def test_user(db_session):
    """Create a test user with organization."""
    # Create org
    org = Organization(name="Test Org", is_active=True)
    db_session.add(org)
    await db_session.flush()
    
    # Create user
    user = User(
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    
    # Create membership
    membership = Membership(
        user_id=user.id,
        organization_id=org.id,
        role=UserRole.OWNER,
    )
    db_session.add(membership)
    await db_session.commit()
    
    return {"user": user, "org": org, "membership": membership}


@pytest.fixture
async def auth_token(client, test_user):
    """Get authentication token for test user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user["user"].email,
            "password": "testpassword123",
        },
    )
    return response.json()["token"]["access_token"]


class TestAuthRegister:
    """Tests for POST /api/v1/auth/register."""

    @pytest.mark.asyncio
    async def test_register_success(self, client, db_session):
        """Test successful user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "full_name": "New User",
                "organization_name": "New Company",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "User registered successfully"
        assert data["user"]["email"] == "newuser@example.com"
        assert data["organization"]["name"] == "New Company"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client, test_user, db_session):
        """Test registration with existing email fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user["user"].email,
                "password": "securepassword123",
                "full_name": "Duplicate User",
                "organization_name": "Another Company",
            },
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "already registered" in data["detail"]["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client):
        """Test registration with invalid email fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "securepassword123",
                "full_name": "Test User",
                "organization_name": "Test Company",
            },
        )
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_short_password(self, client):
        """Test registration with short password fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test2@example.com",
                "password": "short",
                "full_name": "Test User",
                "organization_name": "Test Company",
            },
        )
        
        assert response.status_code == 422  # Validation error


class TestAuthLogin:
    """Tests for POST /api/v1/auth/login."""

    @pytest.mark.asyncio
    async def test_login_success(self, client, test_user, db_session):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["user"].email,
                "password": "testpassword123",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "access_token" in data["token"]
        assert data["token"]["token_type"] == "bearer"
        assert data["user"]["email"] == test_user["user"].email
        assert data["organization"]["name"] == test_user["org"].name

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, test_user, db_session):
        """Test login with wrong password fails."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["user"].email,
                "password": "wrongpassword",
            },
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "invalid credentials" in data["detail"]["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client, db_session):
        """Test login with non-existent user fails."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "anypassword",
            },
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client, db_session):
        """Test login with inactive user fails."""
        # Create inactive user
        org = Organization(name="Test Org 2", is_active=True)
        db_session.add(org)
        await db_session.flush()
        
        user = User(
            email="inactive@example.com",
            hashed_password=hash_password("password123"),
            is_active=False,
        )
        db_session.add(user)
        await db_session.commit()
        
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "password123",
            },
        )
        
        assert response.status_code == 403


class TestAuthRefresh:
    """Tests for POST /api/v1/auth/refresh."""

    @pytest.mark.asyncio
    async def test_refresh_success(self, client, test_user, db_session):
        """Test successful token refresh."""
        # First login to get token
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["user"].email,
                "password": "testpassword123",
            },
        )
        token = login_response.json()["token"]["access_token"]
        
        # Refresh token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"access_token": token},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "access_token" in data["token"]
        assert data["user"]["email"] == test_user["user"].email

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client, db_session):
        """Test refresh with invalid token fails."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"access_token": "invalid.token.here"},
        )
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_expired_token(self, client, db_session):
        """Test refresh with expired token fails."""
        # Create expired token (manual construction for test)
        from datetime import datetime, timedelta, timezone
        from jose import jwt
        from app.core.config import settings
        
        expired_payload = {
            "sub": "999",  # Non-existent user
            "org_id": None,
            "role": None,
            "permissions": [],
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=25),
        }
        expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm="HS256")
        
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"access_token": expired_token},
        )
        
        assert response.status_code == 401


class TestAuthJWTTokens:
    """Tests for JWT token structure and claims."""

    @pytest.mark.asyncio
    async def test_token_contains_org_id(self, client, test_user, db_session):
        """Test that login token contains org_id claim."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["user"].email,
                "password": "testpassword123",
            },
        )
        
        token = response.json()["token"]["access_token"]
        
        # Decode and verify claims
        from app.core.tokens import decode_token
        payload = decode_token(token)
        
        assert payload is not None
        assert payload.sub == str(test_user["user"].id)
        assert payload.org_id == test_user["org"].id

    @pytest.mark.asyncio
    async def test_token_contains_role(self, client, test_user, db_session):
        """Test that login token contains role claim."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["user"].email,
                "password": "testpassword123",
            },
        )
        
        token = response.json()["token"]["access_token"]
        
        from app.core.tokens import decode_token
        payload = decode_token(token)
        
        assert payload.role == UserRole.OWNER.value

    @pytest.mark.asyncio
    async def test_token_contains_permissions(self, client, test_user, db_session):
        """Test that login token contains permissions claim."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["user"].email,
                "password": "testpassword123",
            },
        )
        
        token = response.json()["token"]["access_token"]
        
        from app.core.tokens import decode_token
        payload = decode_token(token)
        
        assert payload.permissions is not None
        assert len(payload.permissions) > 0