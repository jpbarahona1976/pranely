"""Tests for Residue API endpoints."""
import pytest
from httpx import AsyncClient


@pytest.fixture
async def auth_token(client: AsyncClient, db):
    """Get auth token for testing."""
    from app.models import Membership, Organization, User, UserRole
    from app.core.security import hash_password
    
    org = Organization(name="Residue Test Org")
    db.add(org)
    await db.flush()
    
    user = User(
        email="residue_test@test.com",
        hashed_password=hash_password("TestPass123!"),
    )
    db.add(user)
    await db.flush()
    
    membership = Membership(user_id=user.id, organization_id=org.id, role=UserRole.MEMBER)
    db.add(membership)
    await db.flush()
    
    response = await client.post(
        "/api/auth/login",
        json={"email": "residue_test@test.com", "password": "TestPass123!"},
    )
    return response.json()["token"]["access_token"]


@pytest.fixture
async def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
async def test_employer_id(client: AsyncClient, auth_headers):
    """Create a test employer and return its ID."""
    response = await client.post(
        "/api/employers",
        headers=auth_headers,
        json={
            "name": "Test Employer for Residue",
            "rfc": "XAA240601001",
            "address": "Test Address",
        },
    )
    return response.json()["id"]


@pytest.fixture
async def test_transporter_id(client: AsyncClient, auth_headers):
    """Create a test transporter and return its ID."""
    response = await client.post(
        "/api/transporters",
        headers=auth_headers,
        json={
            "name": "Test Transporter for Residue",
            "rfc": "XAA240601002",
            "address": "Test Address",
        },
    )
    return response.json()["id"]


# =============================================================================
# Tests: Residue CRUD
# =============================================================================

class TestResidueCreate:
    """Tests for residue creation."""

    @pytest.mark.asyncio
    async def test_create_residue_success(self, client: AsyncClient, auth_headers, test_employer_id):
        """Test successful residue creation."""
        response = await client.post(
            "/api/residues",
            headers=auth_headers,
            json={
                "name": "Baterías de litio",
                "employer_id": test_employer_id,
                "waste_type": "peligroso",
                "un_code": "UN3480",
                "hs_code": "8507.60",
                "description": "Baterías agotadas",
                "weight_kg": 150.5,
                "volume_m3": 0.5,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Baterías de litio"
        assert data["waste_type"] == "peligroso"
        assert data["weight_kg"] == 150.5
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_residue_with_transporter(self, client: AsyncClient, auth_headers, test_employer_id, test_transporter_id):
        """Test residue creation with transporter."""
        response = await client.post(
            "/api/residues",
            headers=auth_headers,
            json={
                "name": "Residuo con transporte",
                "employer_id": test_employer_id,
                "transporter_id": test_transporter_id,
                "waste_type": "especial",
                "weight_kg": 100.0,
            },
        )
        
        assert response.status_code == 201
        assert response.json()["transporter_id"] == test_transporter_id

    @pytest.mark.asyncio
    async def test_create_residue_invalid_employer(self, client: AsyncClient, auth_headers):
        """Test residue creation fails with non-existent employer."""
        response = await client.post(
            "/api/residues",
            headers=auth_headers,
            json={
                "name": "Test",
                "employer_id": 99999,
                "waste_type": "peligroso",
            },
        )
        
        assert response.status_code == 404
        assert "Employer" in response.json()["detail"]["detail"]

    @pytest.mark.asyncio
    async def test_create_residue_invalid_transporter(self, client: AsyncClient, auth_headers, test_employer_id):
        """Test residue creation fails with non-existent transporter."""
        response = await client.post(
            "/api/residues",
            headers=auth_headers,
            json={
                "name": "Test",
                "employer_id": test_employer_id,
                "transporter_id": 99999,
                "waste_type": "peligroso",
            },
        )
        
        assert response.status_code == 404
        assert "Transporter" in response.json()["detail"]["detail"]


class TestResidueList:
    """Tests for residue list."""

    @pytest.mark.asyncio
    async def test_list_residues_empty(self, client: AsyncClient, auth_headers):
        """Test listing residues when none exist."""
        response = await client.get("/api/residues", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["items"] == []

    @pytest.mark.asyncio
    async def test_list_residues_with_data(self, client: AsyncClient, auth_headers, test_employer_id):
        """Test listing residues with data."""
        for i in range(3):
            await client.post(
                "/api/residues",
                headers=auth_headers,
                json={
                    "name": f"Residue {i}",
                    "employer_id": test_employer_id,
                    "waste_type": "inerte",
                },
            )
        
        response = await client.get("/api/residues", headers=auth_headers)
        
        assert response.status_code == 200
        assert len(response.json()["items"]) == 3

    @pytest.mark.asyncio
    async def test_list_residues_filter_by_employer(self, client: AsyncClient, auth_headers, test_employer_id):
        """Test filtering residues by employer."""
        # Create another employer
        emp_resp = await client.post(
            "/api/employers",
            headers=auth_headers,
            json={
                "name": "Another Employer",
                "rfc": "XAA240601003",
                "address": "Addr",
            },
        )
        emp2_id = emp_resp.json()["id"]
        
        # Create residues for both employers
        await client.post(
            "/api/residues",
            headers=auth_headers,
            json={"name": "Residue 1", "employer_id": test_employer_id, "waste_type": "inerte"},
        )
        await client.post(
            "/api/residues",
            headers=auth_headers,
            json={"name": "Residue 2", "employer_id": emp2_id, "waste_type": "inerte"},
        )
        
        # Filter by first employer
        response = await client.get(
            f"/api/residues?employer_id={test_employer_id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        assert len(response.json()["items"]) == 1
        assert response.json()["items"][0]["name"] == "Residue 1"


class TestResidueGet:
    """Tests for residue get by ID."""

    @pytest.mark.asyncio
    async def test_get_residue_success(self, client: AsyncClient, auth_headers, test_employer_id):
        """Test getting residue by ID."""
        create_resp = await client.post(
            "/api/residues",
            headers=auth_headers,
            json={
                "name": "Get Test Residue",
                "employer_id": test_employer_id,
                "waste_type": "organico",
            },
        )
        residue_id = create_resp.json()["id"]
        
        response = await client.get(f"/api/residues/{residue_id}", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test Residue"

    @pytest.mark.asyncio
    async def test_get_residue_not_found(self, client: AsyncClient, auth_headers):
        """Test getting non-existent residue."""
        response = await client.get("/api/residues/99999", headers=auth_headers)
        
        assert response.status_code == 404


class TestResidueUpdate:
    """Tests for residue update."""

    @pytest.mark.asyncio
    async def test_update_residue_success(self, client: AsyncClient, auth_headers, test_employer_id):
        """Test updating residue."""
        create_resp = await client.post(
            "/api/residues",
            headers=auth_headers,
            json={
                "name": "Original Residue",
                "employer_id": test_employer_id,
                "waste_type": "inerte",
                "weight_kg": 50.0,
            },
        )
        residue_id = create_resp.json()["id"]
        
        response = await client.patch(
            f"/api/residues/{residue_id}",
            headers=auth_headers,
            json={
                "name": "Updated Residue",
                "weight_kg": 75.0,
                "status": "active",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Residue"
        assert data["weight_kg"] == 75.0
        assert data["status"] == "active"


class TestResidueDelete:
    """Tests for residue deletion."""

    @pytest.mark.asyncio
    async def test_delete_residue_success(self, client: AsyncClient, auth_headers, test_employer_id):
        """Test deleting residue."""
        create_resp = await client.post(
            "/api/residues",
            headers=auth_headers,
            json={
                "name": "Delete Test Residue",
                "employer_id": test_employer_id,
                "waste_type": "reciclable",
            },
        )
        residue_id = create_resp.json()["id"]
        
        response = await client.delete(f"/api/residues/{residue_id}", headers=auth_headers)
        
        assert response.status_code == 204
        
        # Verify it's gone
        get_resp = await client.get(f"/api/residues/{residue_id}", headers=auth_headers)
        assert get_resp.status_code == 404