"""Tests for Transporter API endpoints."""
import pytest
from httpx import AsyncClient


@pytest.fixture
async def auth_token(client: AsyncClient, db):
    """Get auth token for testing."""
    from app.models import Membership, Organization, User, UserRole
    from app.core.security import hash_password
    
    org = Organization(name="Transporter Test Org")
    db.add(org)
    await db.flush()
    
    user = User(
        email="transporter_test@test.com",
        hashed_password=hash_password("TestPass123!"),
    )
    db.add(user)
    await db.flush()
    
    membership = Membership(user_id=user.id, organization_id=org.id, role=UserRole.MEMBER)
    db.add(membership)
    await db.flush()
    
    response = await client.post(
        "/api/auth/login",
        json={"email": "transporter_test@test.com", "password": "TestPass123!"},
    )
    return response.json()["token"]["access_token"]


@pytest.fixture
async def auth_token2(client: AsyncClient, db):
    """Get auth token for second tenant."""
    from app.models import Membership, Organization, User, UserRole
    from app.core.security import hash_password
    
    org2 = Organization(name="Transporter Test Org 2")
    db.add(org2)
    await db.flush()
    
    user2 = User(email="transporter_test2@test.com", hashed_password=hash_password("TestPass123!"))
    db.add(user2)
    await db.flush()
    
    membership2 = Membership(user_id=user2.id, organization_id=org2.id, role=UserRole.MEMBER)
    db.add(membership2)
    await db.flush()
    
    response = await client.post(
        "/api/auth/login",
        json={"email": "transporter_test2@test.com", "password": "TestPass123!"},
    )
    return response.json()["token"]["access_token"]


@pytest.fixture
async def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
async def auth_headers2(auth_token2):
    return {"Authorization": f"Bearer {auth_token2}"}


# =============================================================================
# Tests: Transporter CRUD
# =============================================================================

class TestTransporterCreate:
    """Tests for transporter creation."""

    @pytest.mark.asyncio
    async def test_create_transporter_success(self, client: AsyncClient, auth_headers):
        """Test successful transporter creation."""
        response = await client.post(
            "/api/transporters",
            headers=auth_headers,
            json={
                "name": "Transportes Rápidos SA",
                "rfc": "XAA240501001",
                "address": "Av. Principal 456, CDMX",
                "license_number": "SEMARNAT-2024-001",
                "vehicle_plate": "ABC-1234",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Transportes Rápidos SA"
        assert data["license_number"] == "SEMARNAT-2024-001"
        assert data["vehicle_plate"] == "ABC-1234"

    @pytest.mark.asyncio
    async def test_create_transporter_duplicate_rfc(self, client: AsyncClient, auth_headers):
        """Test transporter creation fails with duplicate RFC."""
        await client.post(
            "/api/transporters",
            headers=auth_headers,
            json={"name": "First Trans", "rfc": "XAA240501002", "address": "Addr 1"},
        )
        
        response = await client.post(
            "/api/transporters",
            headers=auth_headers,
            json={"name": "Second Trans", "rfc": "XAA240501002", "address": "Addr 2"},
        )
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]["detail"]


class TestTransporterList:
    """Tests for transporter list."""

    @pytest.mark.asyncio
    async def test_list_transporters_empty(self, client: AsyncClient, auth_headers):
        """Test listing transporters when none exist."""
        response = await client.get("/api/transporters", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["items"] == []

    @pytest.mark.asyncio
    async def test_list_transporters_with_data(self, client: AsyncClient, auth_headers):
        """Test listing transporters with data."""
        for i in range(3):
            await client.post(
                "/api/transporters",
                headers=auth_headers,
                json={
                    "name": f"Transport {i}",
                    "rfc": f"XAA24050101{i}",
                    "address": f"Addr {i}",
                },
            )
        
        response = await client.get("/api/transporters", headers=auth_headers)
        
        assert response.status_code == 200
        assert len(response.json()["items"]) == 3


class TestTransporterGet:
    """Tests for transporter get by ID."""

    @pytest.mark.asyncio
    async def test_get_transporter_success(self, client: AsyncClient, auth_headers):
        """Test getting transporter by ID."""
        create_resp = await client.post(
            "/api/transporters",
            headers=auth_headers,
            json={
                "name": "Get Test Trans",
                "rfc": "XAA240501020",
                "address": "Address",
            },
        )
        trans_id = create_resp.json()["id"]
        
        response = await client.get(f"/api/transporters/{trans_id}", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test Trans"

    @pytest.mark.asyncio
    async def test_get_transporter_not_found(self, client: AsyncClient, auth_headers):
        """Test getting non-existent transporter."""
        response = await client.get("/api/transporters/99999", headers=auth_headers)
        
        assert response.status_code == 404


class TestTransporterUpdate:
    """Tests for transporter update."""

    @pytest.mark.asyncio
    async def test_update_transporter_success(self, client: AsyncClient, auth_headers):
        """Test updating transporter."""
        create_resp = await client.post(
            "/api/transporters",
            headers=auth_headers,
            json={
                "name": "Original Trans",
                "rfc": "XAA240501030",
                "address": "Original Addr",
            },
        )
        trans_id = create_resp.json()["id"]
        
        response = await client.patch(
            f"/api/transporters/{trans_id}",
            headers=auth_headers,
            json={"name": "Updated Trans", "vehicle_plate": "XYZ-9999"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Trans"
        assert data["vehicle_plate"] == "XYZ-9999"


class TestTransporterDelete:
    """Tests for transporter archive."""

    @pytest.mark.asyncio
    async def test_archive_transporter_success(self, client: AsyncClient, auth_headers):
        """Test archiving transporter."""
        create_resp = await client.post(
            "/api/transporters",
            headers=auth_headers,
            json={
                "name": "Archive Trans",
                "rfc": "XAA240501040",
                "address": "Address",
            },
        )
        trans_id = create_resp.json()["id"]
        
        response = await client.delete(f"/api/transporters/{trans_id}", headers=auth_headers)
        
        assert response.status_code == 204


# =============================================================================
# Tests: Tenant Isolation
# =============================================================================

class TestTransporterTenantIsolation:
    """Tests for transporter tenant isolation."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_org_transporter(self, client: AsyncClient, auth_headers, auth_headers2):
        """Test transporter from one org not accessible by another org."""
        create_resp = await client.post(
            "/api/transporters",
            headers=auth_headers,
            json={
                "name": "Org1 Trans",
                "rfc": "XAA240501050",
                "address": "Address",
            },
        )
        trans_id = create_resp.json()["id"]
        
        response = await client.get(f"/api/transporters/{trans_id}", headers=auth_headers2)
        
        assert response.status_code == 404