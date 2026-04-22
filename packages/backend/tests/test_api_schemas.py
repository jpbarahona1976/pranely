"""Tests for API schemas."""
import pytest
from pydantic import ValidationError

from app.schemas.api.common import (
    PaginationParams,
    ListResponse,
    ErrorResponse,
    ErrorDetail,
)
from app.schemas.api.auth import (
    LoginIn,
    RegisterIn,
    TokenOut,
    UserOut,
    OrgOut,
)
from app.schemas.api.employer import EmployerIn, EmployerOut, EmployerUpdateIn
from app.schemas.api.transporter import TransporterIn, TransporterOut, TransporterUpdateIn
from app.schemas.api.residue import ResidueIn, ResidueOut, ResidueUpdateIn
from app.schemas.api.link import LinkIn, LinkOut, LinkUpdateIn


class TestCommonSchemas:
    """Test common API schemas."""

    def test_pagination_params_defaults(self):
        """Test pagination params have correct defaults."""
        params = PaginationParams()
        assert params.page == 1
        assert params.page_size == 20

    def test_pagination_params_custom(self):
        """Test pagination params accept custom values."""
        params = PaginationParams(page=5, page_size=50)
        assert params.page == 5
        assert params.page_size == 50

    def test_pagination_params_validation(self):
        """Test pagination validation."""
        with pytest.raises(ValidationError):
            PaginationParams(page=0)  # Must be >= 1
        
        with pytest.raises(ValidationError):
            PaginationParams(page_size=200)  # Must be <= 100

    def test_list_response_generic(self):
        """Test ListResponse is generic."""
        items = [{"id": 1}, {"id": 2}]
        response = ListResponse(items=items, total=2, page=1, page_size=20, pages=1)
        assert len(response.items) == 2
        assert response.total == 2

    def test_error_response(self):
        """Test ErrorResponse format (RFC 7807)."""
        error = ErrorResponse(
            type="https://api.pranely.com/errors/employer",
            title="Duplicate RFC",
            status=400,
            detail="RFC already exists in organization",
        )
        assert error.type.startswith("https://")
        assert error.status == 400

    def test_error_response_with_details(self):
        """Test ErrorResponse with field-level errors."""
        error = ErrorResponse(
            type="https://api.pranely.com/errors/validation",
            title="Validation Error",
            status=422,
            detail="Request validation failed",
            errors=[
                ErrorDetail(field="email", message="Invalid email format"),
            ]
        )
        assert error.errors is not None
        assert len(error.errors) == 1
        assert error.errors[0].field == "email"


class TestAuthSchemas:
    """Test auth API schemas."""

    def test_login_in_valid(self):
        """Test LoginIn accepts valid data."""
        login = LoginIn(email="user@test.com", password="password123")
        assert login.email == "user@test.com"
        assert login.password == "password123"

    def test_login_in_invalid_email(self):
        """Test LoginIn rejects invalid email."""
        with pytest.raises(ValidationError):
            LoginIn(email="not-an-email", password="password")

    def test_register_in_valid(self):
        """Test RegisterIn accepts valid data."""
        register = RegisterIn(
            email="user@test.com",
            password="password123",
            full_name="Test User",
            organization_name="Test Org",
        )
        assert register.full_name == "Test User"
        assert register.organization_name == "Test Org"

    def test_register_in_password_min_length(self):
        """Test RegisterIn enforces password min length."""
        with pytest.raises(ValidationError):
            RegisterIn(
                email="user@test.com",
                password="short",  # < 8 chars
                full_name="Test User",
                organization_name="Test Org",
            )

    def test_user_out(self):
        """Test UserOut response."""
        user = UserOut(
            id=1,
            email="user@test.com",
            full_name="Test User",
            locale="es",
            is_active=True,
            created_at="2026-04-23T10:00:00Z",
        )
        assert user.id == 1
        assert user.locale == "es"


class TestEmployerSchemas:
    """Test employer API schemas."""

    def test_employer_in_valid(self):
        """Test EmployerIn accepts valid data."""
        employer = EmployerIn(
            name="Empresa Test",
            rfc="TEST123456789",
            address="Calle 123, Monterrey",
            industry="manufactura",
        )
        assert employer.name == "Empresa Test"
        assert employer.rfc == "TEST123456789"

    def test_employer_in_default_status(self):
        """Test EmployerIn has default status."""
        employer = EmployerIn(
            name="Empresa Test",
            rfc="TEST123456789",
            address="Calle 123",
        )
        assert employer.status == "active"

    def test_employer_in_rfc_format(self):
        """Test EmployerIn validates RFC format."""
        with pytest.raises(ValidationError):
            EmployerIn(
                name="Test",
                rfc="TOOSHORT",  # Must be 12-13 chars
                address="Test",
            )

    def test_employer_out(self):
        """Test EmployerOut response."""
        employer = EmployerOut(
            id=1,
            organization_id=1,
            name="Empresa Test",
            rfc="TEST123456789",
            address="Calle 123",
            status="active",
            created_at="2026-04-23T10:00:00Z",
        )
        assert employer.organization_id == 1
        assert employer.archived_at is None

    def test_employer_update_in_partial(self):
        """Test EmployerUpdateIn allows partial updates."""
        update = EmployerUpdateIn(name="New Name")
        assert update.name == "New Name"
        assert update.rfc is None


class TestTransporterSchemas:
    """Test transporter API schemas."""

    def test_transporter_in_valid(self):
        """Test TransporterIn accepts valid data."""
        transporter = TransporterIn(
            name="Transportes Test",
            rfc="TRT123456789",
            address="Carretera 45",
            license_number="SEMARNAT-2024-001",
            vehicle_plate="ABC-1234",
        )
        assert transporter.license_number == "SEMARNAT-2024-001"
        assert transporter.vehicle_plate == "ABC-1234"

    def test_transporter_out(self):
        """Test TransporterOut response."""
        transporter = TransporterOut(
            id=1,
            organization_id=1,
            name="Transportes Test",
            rfc="TRT123456789",
            address="Carretera 45",
            status="active",
            created_at="2026-04-23T10:00:00Z",
        )
        assert transporter.organization_id == 1


class TestResidueSchemas:
    """Test residue API schemas."""

    def test_residue_in_valid(self):
        """Test ResidueIn accepts valid data."""
        residue = ResidueIn(
            employer_id=1,
            name="Residuo Test",
            waste_type="peligroso",
            weight_kg=500.5,
            volume_m3=2.0,
        )
        assert residue.employer_id == 1
        assert residue.waste_type == "peligroso"
        assert residue.weight_kg == 500.5

    def test_residue_in_optional_transporter(self):
        """Test ResidueIn allows optional transporter."""
        residue = ResidueIn(
            employer_id=1,
            name="Residuo Test",
            waste_type="especial",
            transporter_id=None,
        )
        assert residue.transporter_id is None

    def test_residue_in_weight_validation(self):
        """Test ResidueIn validates weight >= 0."""
        with pytest.raises(ValidationError):
            ResidueIn(
                employer_id=1,
                name="Test",
                waste_type="peligroso",
                weight_kg=-100,  # Must be >= 0
            )

    def test_residue_out(self):
        """Test ResidueOut response."""
        residue = ResidueOut(
            id=1,
            organization_id=1,
            employer_id=1,
            name="Residuo Test",
            waste_type="peligroso",
            status="pending",
            created_at="2026-04-23T10:00:00Z",
        )
        assert residue.organization_id == 1


class TestLinkSchemas:
    """Test link API schemas."""

    def test_link_in_valid(self):
        """Test LinkIn accepts valid data."""
        link = LinkIn(
            employer_id=1,
            transporter_id=2,
            is_authorized=True,
            notes="Autorizado",
        )
        assert link.employer_id == 1
        assert link.transporter_id == 2
        assert link.is_authorized is True

    def test_link_in_default_authorized(self):
        """Test LinkIn defaults to is_authorized=True."""
        link = LinkIn(
            employer_id=1,
            transporter_id=2,
        )
        assert link.is_authorized is True

    def test_link_out(self):
        """Test LinkOut response."""
        link = LinkOut(
            id=1,
            organization_id=1,
            employer_id=1,
            transporter_id=2,
            is_authorized=True,
            created_at="2026-04-23T10:00:00Z",
        )
        assert link.organization_id == 1

    def test_link_update_in_partial(self):
        """Test LinkUpdateIn allows partial updates."""
        update = LinkUpdateIn(is_authorized=False)
        assert update.is_authorized is False
        assert update.notes is None


class TestSchemaMultiTenant:
    """Test schemas include organization_id for multi-tenancy."""

    def test_employer_out_has_org_id(self):
        """EmployerOut must have organization_id."""
        employer = EmployerOut(
            id=1,
            organization_id=5,
            name="Test",
            rfc="TEST123456789",
            address="Test",
            status="active",
            created_at="2026-04-23T10:00:00Z",
        )
        assert employer.organization_id == 5

    def test_transporter_out_has_org_id(self):
        """TransporterOut must have organization_id."""
        t = TransporterOut(
            id=1,
            organization_id=3,
            name="Test",
            rfc="TEST123456789",
            address="Test",
            status="active",
            created_at="2026-04-23T10:00:00Z",
        )
        assert t.organization_id == 3

    def test_residue_out_has_org_id(self):
        """ResidueOut must have organization_id."""
        r = ResidueOut(
            id=1,
            organization_id=7,
            employer_id=1,
            name="Test",
            waste_type="peligroso",
            status="pending",
            created_at="2026-04-23T10:00:00Z",
        )
        assert r.organization_id == 7

    def test_link_out_has_org_id(self):
        """LinkOut must have organization_id."""
        link = LinkOut(
            id=1,
            organization_id=2,
            employer_id=1,
            transporter_id=3,
            is_authorized=True,
            created_at="2026-04-23T10:00:00Z",
        )
        assert link.organization_id == 2