"""Tests for EmployerTransporterLink API endpoints."""
import pytest
from httpx import AsyncClient


@pytest.fixture
async def auth_token(client: AsyncClient, db):
    """Get auth token for testing."""
    from app.models import Membership, Organization, User, UserRole
    from app.core.security import hash_password
    
    org = Organization(name="Link Test Org")
    db.add(org)
    await db.flush()
    
    user = User(
        email="link_test@test.com",
        hashed_password=hash_password("TestPass123!"),
    )
    db.add(user)
    await db.flush()
    
    membership = Membership(user_id=user.id, organization_id=org.id, role=UserRole.MEMBER)
    db.add(membership)
    await db.flush()
    
    response = await client.post(
        "/api/auth/login",
        json={"email": "link_test@test.com", "password": "TestPass123!"},
    )
    return response.json()["token"]["access_token"]


@pytest.fixture
async def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
async def test_employer(client: AsyncClient, auth_headers):
    """Create a test employer."""
    response = await client.post(
        "/api/employers",
        headers=auth_headers,
        json={
            "name": "Link Test Employer",
            "rfc": "XAA240701001",
            "address": "Test Address",
        },
    )
    return response.json()


@pytest.fixture
async def test_transporter(client: AsyncClient, auth_headers):
    """Create a test transporter."""
    response = await client.post(
        "/api/transporters",
        headers=auth_headers,
        json={
            "name": "Link Test Transporter",
            "rfc": "XAA240701002",
            "address": "Test Address",
        },
    )
    return response.json()


# =============================================================================
# Tests: Link CRUD
# =============================================================================

class TestLinkCreate:
    """Tests for link creation."""

    @pytest.mark.asyncio
    async def test_create_link_success(self, client: AsyncClient, auth_headers, test_employer, test_transporter):
        """Test successful link creation."""
        response = await client.post(
            "/api/employer-transporter-links",
            headers=auth_headers,
            json={
                "employer_id": test_employer["id"],
                "transporter_id": test_transporter["id"],
                "is_authorized": True,
                "notes": "Autorizado para residuos peligrosos",
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["employer_id"] == test_employer["id"]
        assert data["transporter_id"] == test_transporter["id"]
        assert data["is_authorized"] is True
        assert data["notes"] == "Autorizado para residuos peligrosos"

    @pytest.mark.asyncio
    async def test_create_link_invalid_employer(self, client: AsyncClient, auth_headers, test_transporter):
        """Test link creation fails with non-existent employer."""
        response = await client.post(
            "/api/employer-transporter-links",
            headers=auth_headers,
            json={
                "employer_id": 99999,
                "transporter_id": test_transporter["id"],
            },
        )
        
        assert response.status_code == 404
        assert "Employer" in response.json()["detail"]["detail"]

    @pytest.mark.asyncio
    async def test_create_link_invalid_transporter(self, client: AsyncClient, auth_headers, test_employer):
        """Test link creation fails with non-existent transporter."""
        response = await client.post(
            "/api/employer-transporter-links",
            headers=auth_headers,
            json={
                "employer_id": test_employer["id"],
                "transporter_id": 99999,
            },
        )
        
        assert response.status_code == 404
        assert "Transporter" in response.json()["detail"]["detail"]

    @pytest.mark.asyncio
    async def test_create_duplicate_link(self, client: AsyncClient, auth_headers, test_employer, test_transporter):
        """Test creating duplicate link fails."""
        # Create first link
        await client.post(
            "/api/employer-transporter-links",
            headers=auth_headers,
            json={
                "employer_id": test_employer["id"],
                "transporter_id": test_transporter["id"],
            },
        )
        
        # Try to create duplicate
        response = await client.post(
            "/api/employer-transporter-links",
            headers=auth_headers,
            json={
                "employer_id": test_employer["id"],
                "transporter_id": test_transporter["id"],
            },
        )
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]["detail"]


class TestLinkList:
    """Tests for link list."""

    @pytest.mark.asyncio
    async def test_list_links_empty(self, client: AsyncClient, auth_headers):
        """Test listing links when none exist."""
        response = await client.get("/api/employer-transporter-links", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_links_with_data(self, client: AsyncClient, auth_headers, test_employer):
        """Test listing links with data."""
        # Create another transporter
        trans_resp = await client.post(
            "/api/transporters",
            headers=auth_headers,
            json={
                "name": "Second Transporter",
                "rfc": "XAA240701003",
                "address": "Address",
            },
        )
        trans2_id = trans_resp.json()["id"]
        
        # Create links
        await client.post(
            "/api/employer-transporter-links",
            headers=auth_headers,
            json={"employer_id": test_employer["id"], "transporter_id": trans2_id},
        )
        
        response = await client.get("/api/employer-transporter-links", headers=auth_headers)
        
        assert response.status_code == 200
        assert len(response.json()) >= 1

    @pytest.mark.asyncio
    async def test_list_links_filter_by_employer(self, client: AsyncClient, auth_headers):
        """Test filtering links by employer."""
        # Create employer and transporters
        emp_resp = await client.post(
            "/api/employers",
            headers=auth_headers,
            json={"name": "Filter Emp", "rfc": "XAA240701004", "address": "Addr"},
        )
        emp_id = emp_resp.json()["id"]
        
        trans_resp1 = await client.post(
            "/api/transporters",
            headers=auth_headers,
            json={"name": "Filter Trans 1", "rfc": "XAA240701005", "address": "Addr"},
        )
        trans_resp2 = await client.post(
            "/api/transporters",
            headers=auth_headers,
            json={"name": "Filter Trans 2", "rfc": "XAA240701006", "address": "Addr"},
        )
        
        # Create links
        await client.post(
            "/api/employer-transporter-links",
            headers=auth_headers,
            json={"employer_id": emp_id, "transporter_id": trans_resp1.json()["id"]},
        )
        await client.post(
            "/api/employer-transporter-links",
            headers=auth_headers,
            json={"employer_id": emp_id, "transporter_id": trans_resp2.json()["id"]},
        )
        
        # Filter by employer
        response = await client.get(
            f"/api/employer-transporter-links?employer_id={emp_id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        assert len(response.json()) == 2

    @pytest.mark.asyncio
    async def test_list_links_filter_by_authorized(self, client: AsyncClient, auth_headers, test_employer):
        """Test filtering links by authorization status."""
        trans_resp = await client.post(
            "/api/transporters",
            headers=auth_headers,
            json={"name": "Auth Test Trans", "rfc": "XAA240701007", "address": "Addr"},
        )
        
        # Create authorized link
        await client.post(
            "/api/employer-transporter-links",
            headers=auth_headers,
            json={
                "employer_id": test_employer["id"],
                "transporter_id": trans_resp.json()["id"],
                "is_authorized": True,
            },
        )
        
        # Filter by authorized
        response = await client.get(
            "/api/employer-transporter-links?is_authorized=true",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        assert all(link["is_authorized"] for link in response.json())


class TestLinkGet:
    """Tests for link get by ID."""

    @pytest.mark.asyncio
    async def test_get_link_success(self, client: AsyncClient, auth_headers, test_employer, test_transporter):
        """Test getting link by ID."""
        create_resp = await client.post(
            "/api/employer-transporter-links",
            headers=auth_headers,
            json={
                "employer_id": test_employer["id"],
                "transporter_id": test_transporter["id"],
            },
        )
        link_id = create_resp.json()["id"]
        
        response = await client.get(f"/api/employer-transporter-links/{link_id}", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["id"] == link_id

    @pytest.mark.asyncio
    async def test_get_link_not_found(self, client: AsyncClient, auth_headers):
        """Test getting non-existent link."""
        response = await client.get("/api/employer-transporter-links/99999", headers=auth_headers)
        
        assert response.status_code == 404


class TestLinkUpdate:
    """Tests for link update."""

    @pytest.mark.asyncio
    async def test_update_link_success(self, client: AsyncClient, auth_headers, test_employer, test_transporter):
        """Test updating link."""
        create_resp = await client.post(
            "/api/employer-transporter-links",
            headers=auth_headers,
            json={
                "employer_id": test_employer["id"],
                "transporter_id": test_transporter["id"],
                "is_authorized": False,
                "notes": "Original note",
            },
        )
        link_id = create_resp.json()["id"]
        
        response = await client.patch(
            f"/api/employer-transporter-links/{link_id}",
            headers=auth_headers,
            json={
                "is_authorized": True,
                "notes": "Updated note",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_authorized"] is True
        assert data["notes"] == "Updated note"


class TestLinkDelete:
    """Tests for link deletion."""

    @pytest.mark.asyncio
    async def test_delete_link_success(self, client: AsyncClient, auth_headers, test_employer, test_transporter):
        """Test deleting link."""
        create_resp = await client.post(
            "/api/employer-transporter-links",
            headers=auth_headers,
            json={
                "employer_id": test_employer["id"],
                "transporter_id": test_transporter["id"],
            },
        )
        link_id = create_resp.json()["id"]
        
        response = await client.delete(f"/api/employer-transporter-links/{link_id}", headers=auth_headers)
        
        assert response.status_code == 204
        
        # Verify it's gone
        get_resp = await client.get(f"/api/employer-transporter-links/{link_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_link_not_found(self, client: AsyncClient, auth_headers):
        """Test deleting non-existent link."""
        response = await client.delete("/api/employer-transporter-links/99999", headers=auth_headers)
        
        assert response.status_code == 404