"""Tests for Employer API endpoints."""
import pytest
from httpx import AsyncClient

from app.models import EntityStatus


@pytest.fixture
async def org_user(db):
    """Create org + user + membership for testing."""
    from app.models import Membership, Organization, User, UserRole
    from app.core.security import hash_password
    
    # Create org
    org = Organization(name="API Test Org")
    db.add(org)
    await db.flush()
    
    # Create user
    user = User(
        email="api_test@test.com",
        hashed_password=hash_password("TestPass123!"),
        full_name="API Test User",
    )
    db.add(user)
    await db.flush()
    
    # Create membership
    membership = Membership(
        user_id=user.id,
        organization_id=org.id,
        role=UserRole.MEMBER,
    )
    db.add(membership)
    await db.flush()
    
    return {"org": org, "user": user, "membership": membership}


@pytest.fixture
async def org_user2(db):
    """Create second org + user for tenant isolation testing."""
    from app.models import Membership, Organization, User, UserRole
    from app.core.security import hash_password
    
    # Create org2
    org2 = Organization(name="API Test Org 2")
    db.add(org2)
    await db.flush()
    
    # Create user2
    user2 = User(
        email="api_test2@test.com",
        hashed_password=hash_password("TestPass123!"),
        full_name="API Test User 2",
    )
    db.add(user2)
    await db.flush()
    
    # Create membership
    membership2 = Membership(
        user_id=user2.id,
        organization_id=org2.id,
        role=UserRole.MEMBER,
    )
    db.add(membership2)
    await db.flush()
    
    return {"org": org2, "user": user2, "membership": membership2}


@pytest.fixture
async def auth_token(client: AsyncClient, org_user):
    """Get auth token for testing."""
    # Login to get token
    response = await client.post(
        "/api/auth/login",
        json={"email": "api_test@test.com", "password": "TestPass123!"},
    )
    assert response.status_code == 200
    return response.json()["token"]["access_token"]


@pytest.fixture
async def auth_token2(client: AsyncClient, org_user2):
    """Get auth token for second tenant."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "api_test2@test.com", "password": "TestPass123!"},
    )
    assert response.status_code == 200
    return response.json()["token"]["access_token"]


@pytest.fixture
async def auth_headers(auth_token):
    """Get authorization headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
async def auth_headers2(auth_token2):
    """Get authorization headers for second tenant."""
    return {"Authorization": f"Bearer {auth_token2}"}


# =============================================================================
# Tests: Employer CRUD
# =============================================================================

class TestEmployerCreate:
    """Tests for employer creation endpoint."""

    @pytest.mark.asyncio
    async def test_create_employer_success(self, client: AsyncClient, auth_headers, db):
        """Test successful employer creation."""
        response = await client.post(
            "/api/employers",
            headers=auth_headers,
            json={
                "name": "Test Employer SA",
                "rfc": "XAA240401001",
                "address": "Calle Test 123, CDMX",
                "contact_phone": "+52 55 1234 5678",
                "email": "test@employer.com",
                "industry": "Manufacturing",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Employer SA"
        assert data["rfc"] == "XAA240401001"
        assert data["status"] == "active"
        assert "id" in data
        assert "organization_id" in data

    @pytest.mark.asyncio
    async def test_create_employer_duplicate_rfc(self, client: AsyncClient, auth_headers, db):
        """Test employer creation fails with duplicate RFC."""
        # Create first employer
        await client.post(
            "/api/employers",
            headers=auth_headers,
            json={
                "name": "First Employer",
                "rfc": "XAA240401002",
                "address": "Address 1",
            },
        )
        
        # Try to create second with same RFC
        response = await client.post(
            "/api/employers",
            headers=auth_headers,
            json={
                "name": "Second Employer",
                "rfc": "XAA240401002",
                "address": "Address 2",
            },
        )
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]["detail"]

    @pytest.mark.asyncio
    async def test_create_employer_invalid_rfc(self, client: AsyncClient, auth_headers):
        """Test employer creation fails with invalid RFC."""
        response = await client.post(
            "/api/employers",
            headers=auth_headers,
            json={
                "name": "Test",
                "rfc": "INVALID",
                "address": "Address",
            },
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_employer_unauthorized(self, client: AsyncClient):
        """Test employer creation fails without auth."""
        response = await client.post(
            "/api/employers",
            json={
                "name": "Test",
                "rfc": "XAA240401003",
                "address": "Address",
            },
        )
        
        # 401 = Unauthorized (no token), 403 = Forbidden (authenticated but no permission)
        assert response.status_code == 401


class TestEmployerList:
    """Tests for employer list endpoint."""

    @pytest.mark.asyncio
    async def test_list_employers_empty(self, client: AsyncClient, auth_headers):
        """Test listing employers when none exist."""
        response = await client.get("/api/employers", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_list_employers_with_data(self, client: AsyncClient, auth_headers):
        """Test listing employers with data."""
        # Create some employers
        for i in range(3):
            await client.post(
                "/api/employers",
                headers=auth_headers,
                json={
                    "name": f"Employer {i}",
                    "rfc": f"XAA24040101{i}",
                    "address": f"Address {i}",
                },
            )
        
        response = await client.get("/api/employers", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 3

    @pytest.mark.asyncio
    async def test_list_employers_pagination(self, client: AsyncClient, auth_headers):
        """Test employer list pagination."""
        # Create 5 employers
        for i in range(5):
            await client.post(
                "/api/employers",
                headers=auth_headers,
                json={
                    "name": f"Employer {i}",
                    "rfc": f"XAA24040102{i}",
                    "address": f"Address {i}",
                },
            )
        
        # Request page 1 with page_size 2
        response = await client.get(
            "/api/employers?page=1&page_size=2",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["pages"] == 3

    @pytest.mark.asyncio
    async def test_list_employers_search(self, client: AsyncClient, auth_headers):
        """Test employer list search."""
        await client.post(
            "/api/employers",
            headers=auth_headers,
            json={"name": "Acme Corp", "rfc": "XAA240401030", "address": "Addr"},
        )
        await client.post(
            "/api/employers",
            headers=auth_headers,
            json={"name": "Beta Inc", "rfc": "XAA240401031", "address": "Addr"},
        )
        
        response = await client.get(
            "/api/employers?search=Acme",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Acme Corp"


class TestEmployerGet:
    """Tests for employer get by ID endpoint."""

    @pytest.mark.asyncio
    async def test_get_employer_success(self, client: AsyncClient, auth_headers):
        """Test getting employer by ID."""
        # Create employer
        create_response = await client.post(
            "/api/employers",
            headers=auth_headers,
            json={
                "name": "Get Test Employer",
                "rfc": "XAA240401040",
                "address": "Address",
            },
        )
        employer_id = create_response.json()["id"]
        
        response = await client.get(f"/api/employers/{employer_id}", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test Employer"

    @pytest.mark.asyncio
    async def test_get_employer_not_found(self, client: AsyncClient, auth_headers):
        """Test getting non-existent employer."""
        response = await client.get("/api/employers/99999", headers=auth_headers)
        
        assert response.status_code == 404


class TestEmployerUpdate:
    """Tests for employer update endpoint."""

    @pytest.mark.asyncio
    async def test_update_employer_success(self, client: AsyncClient, auth_headers):
        """Test updating employer."""
        # Create employer
        create_response = await client.post(
            "/api/employers",
            headers=auth_headers,
            json={
                "name": "Original Name",
                "rfc": "XAA240401050",
                "address": "Original Address",
            },
        )
        employer_id = create_response.json()["id"]
        
        response = await client.patch(
            f"/api/employers/{employer_id}",
            headers=auth_headers,
            json={"name": "Updated Name", "address": "Updated Address"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["address"] == "Updated Address"
        assert data["rfc"] == "XAA240401050"  # RFC unchanged

    @pytest.mark.asyncio
    async def test_update_employer_not_found(self, client: AsyncClient, auth_headers):
        """Test updating non-existent employer."""
        response = await client.patch(
            "/api/employers/99999",
            headers=auth_headers,
            json={"name": "New Name"},
        )
        
        assert response.status_code == 404


class TestEmployerDelete:
    """Tests for employer archive (soft delete) endpoint."""

    @pytest.mark.asyncio
    async def test_archive_employer_success(self, client: AsyncClient, auth_headers):
        """Test archiving employer."""
        # Create employer
        create_response = await client.post(
            "/api/employers",
            headers=auth_headers,
            json={
                "name": "Archive Test",
                "rfc": "XAA240401060",
                "address": "Address",
            },
        )
        employer_id = create_response.json()["id"]
        
        # Archive it
        response = await client.delete(f"/api/employers/{employer_id}", headers=auth_headers)
        
        assert response.status_code == 204
        
        # Verify it's gone from normal list
        list_response = await client.get("/api/employers", headers=auth_headers)
        assert all(e["id"] != employer_id for e in list_response.json()["items"])

    @pytest.mark.asyncio
    async def test_archive_employer_not_found(self, client: AsyncClient, auth_headers):
        """Test archiving non-existent employer."""
        response = await client.delete("/api/employers/99999", headers=auth_headers)
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_archive_employer_includes_archived(self, client: AsyncClient, auth_headers):
        """Test archived employer appears when include_archived=true."""
        # Create and archive employer
        create_response = await client.post(
            "/api/employers",
            headers=auth_headers,
            json={
                "name": "Archive Include Test",
                "rfc": "XAA240401070",
                "address": "Address",
            },
        )
        employer_id = create_response.json()["id"]
        await client.delete(f"/api/employers/{employer_id}", headers=auth_headers)
        
        # List with include_archived
        response = await client.get(
            "/api/employers?include_archived=true",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        assert any(e["id"] == employer_id for e in response.json()["items"])


# =============================================================================
# Tests: Multi-tenant Isolation
# =============================================================================

class TestEmployerTenantIsolation:
    """Tests for employer tenant isolation."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_org_employer(self, client: AsyncClient, auth_headers, auth_headers2):
        """Test employer from one org not accessible by another org."""
        # Create employer in org1
        create_response = await client.post(
            "/api/employers",
            headers=auth_headers,
            json={
                "name": "Org1 Employer",
                "rfc": "XAA240401080",
                "address": "Address",
            },
        )
        employer_id = create_response.json()["id"]
        
        # Try to access from org2
        response = await client.get(f"/api/employers/{employer_id}", headers=auth_headers2)
        
        assert response.status_code == 404  # Not found for org2

    @pytest.mark.asyncio
    async def test_org2_cannot_see_org1_employers(self, client: AsyncClient, auth_headers, auth_headers2):
        """Test org2 list doesn't include org1 employers."""
        # Create employer in org1
        await client.post(
            "/api/employers",
            headers=auth_headers,
            json={
                "name": "Org1 Only",
                "rfc": "XAA240401090",
                "address": "Address",
            },
        )
        
        # List from org2
        response = await client.get("/api/employers", headers=auth_headers2)
        
        assert response.status_code == 200
        assert len(response.json()["items"]) == 0  # No employers for org2