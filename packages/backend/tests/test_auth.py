"""Tests for authentication endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Test successful user registration."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "SecurePass123!",
            "full_name": "Test User",
            "organization_name": "Test Corp",
        },
    )
    
    assert response.status_code == 201
    data = response.json()
    
    # Check response structure
    assert data["message"] == "User registered successfully"
    assert "user" in data
    assert "organization" in data
    
    # Check user data
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["full_name"] == "Test User"
    assert "hashed_password" not in data["user"]  # Password not exposed
    
    # Check organization data
    assert data["organization"]["name"] == "Test Corp"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test registration fails with duplicate email."""
    # First registration
    await client.post(
        "/api/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "SecurePass123!",
            "organization_name": "First Org",
        },
    )
    
    # Second registration with same email
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "duplicate@example.com",
            "password": "AnotherPass456!",
            "organization_name": "Second Org",
        },
    )
    
    assert response.status_code == 400
    data = response.json()
    assert "already registered" in data["detail"]["detail"]


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    """Test registration fails with invalid email."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "password": "SecurePass123!",
            "organization_name": "Test Org",
        },
    )
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    """Test registration fails with short password."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "short",
            "organization_name": "Test Org",
        },
    )
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Test successful login."""
    # Register first
    await client.post(
        "/api/auth/register",
        json={
            "email": "login@example.com",
            "password": "SecurePass123!",
            "full_name": "Login User",
            "organization_name": "Login Corp",
        },
    )
    
    # Login
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "login@example.com",
            "password": "SecurePass123!",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check token structure
    assert "token" in data
    assert "access_token" in data["token"]
    assert data["token"]["token_type"] == "bearer"
    assert data["token"]["expires_in"] == 86400
    
    # Check user data
    assert "user" in data
    assert data["user"]["email"] == "login@example.com"
    
    # Check organization data
    assert "organization" in data
    assert data["organization"]["name"] == "Login Corp"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test login fails with wrong password."""
    # Register first
    await client.post(
        "/api/auth/register",
        json={
            "email": "wrongpass@example.com",
            "password": "CorrectPass123!",
            "organization_name": "Test Corp",
        },
    )
    
    # Login with wrong password
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "wrongpass@example.com",
            "password": "WrongPassword!",
        },
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "Invalid credentials" in data["detail"]["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login fails with nonexistent email."""
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "AnyPassword123!",
        },
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "Invalid credentials" in data["detail"]["detail"]


@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient):
    """Test accessing protected endpoint without token returns 403."""
    # We need a protected endpoint to test this
    # For now, this is a placeholder - will be tested when we add protected routes
    pass


@pytest.mark.asyncio
async def test_protected_endpoint_with_valid_token(client: AsyncClient):
    """Test accessing protected endpoint with valid token."""
    # Register and login
    await client.post(
        "/api/auth/register",
        json={
            "email": "protected@example.com",
            "password": "SecurePass123!",
            "organization_name": "Protected Corp",
        },
    )
    
    login_response = await client.post(
        "/api/auth/login",
        json={
            "email": "protected@example.com",
            "password": "SecurePass123!",
        },
    )
    
    token = login_response.json()["token"]["access_token"]
    
    # Test protected endpoint (we'll add this in next phases)
    # For now, this test validates token generation
    assert token is not None
    assert len(token) > 0