"""Tests for domain models: Employer, Residue, Transporter."""
import pytest
from datetime import datetime, timezone

from sqlalchemy import select

from app.models import (
    Base,
    Employer,
    Transporter,
    Residue,
    EmployerTransporterLink,
    EntityStatus,
    WasteType,
    WasteStatus,
    Organization,
    User,
    Membership,
    UserRole,
    # Fase 4A enums
    MovementStatus,
    AlertSeverity,
    AlertStatus,
    SubscriptionStatus,
    BillingPlanCode,
    AuditLogResult,
    # Fase 4A models
    AuditLog,
    BillingPlan,
    Subscription,
    UsageCycle,
    LegalAlert,
    WasteMovement,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def org(db):
    """Create a test organization."""
    org = Organization(name="Test Org Domain")
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@pytest.fixture
async def employer(db, org):
    """Create a test employer."""
    # H1 FIX: RFC válido 13 chars con formato Mexico (incluye Ñ)
    employer = Employer(
        organization_id=org.id,
        name="Acme Industrial",
        rfc="XAA240101ABC",  # 13 chars valid RFC format
        address="Calle Industrial 123, CDMX",
        contact_phone="+52 55 1234 5678",
        email="contacto@acme.com",
        website="https://acme.com",
        industry="Manufacturing",
        status=EntityStatus.ACTIVE,
    )
    db.add(employer)
    await db.commit()
    await db.refresh(employer)
    return employer


@pytest.fixture
async def transporter(db, org):
    """Create a test transporter."""
    # H1 FIX: RFC válido 13 chars con formato Mexico
    transporter = Transporter(
        organization_id=org.id,
        name="Transporte Seguro SA",
        rfc="XAA240102DEF",  # 13 chars valid RFC format
        address="Av. Transporte 456, CDMX",
        contact_phone="+52 55 8765 4321",
        email="operaciones@transporte.com",
        license_number="SEMARNAT-2024-001",
        vehicle_plate="ABC-1234",
        status=EntityStatus.ACTIVE,
    )
    db.add(transporter)
    await db.commit()
    await db.refresh(transporter)
    return transporter


@pytest.fixture
async def residue(db, org, employer):
    """Create a test residue."""
    residue = Residue(
        organization_id=org.id,
        employer_id=employer.id,
        name="Baterias de litio",
        waste_type=WasteType.PELIGROSO,
        un_code="UN3480",
        hs_code="8507.60",
        description="Baterias de iones de litio agotadas",
        weight_kg=150.5,
        volume_m3=0.5,
        status=WasteStatus.PENDING,
    )
    db.add(residue)
    await db.commit()
    await db.refresh(residue)
    return residue


@pytest.fixture
async def link(db, org, employer, transporter):
    """Create an employer-transporter link with organization_id."""
    link = EmployerTransporterLink(
        organization_id=org.id,
        employer_id=employer.id,
        transporter_id=transporter.id,
        is_authorized=True,
        authorization_date=datetime.now(timezone.utc),
        notes="Autorizado para residuos peligrosos",
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


# =============================================================================
# Tests: Enums
# =============================================================================

class TestEnums:
    """Tests for enum definitions."""

    def test_entity_status_values(self):
        """Test EntityStatus enum has correct values."""
        assert EntityStatus.ACTIVE.value == "active"
        assert EntityStatus.INACTIVE.value == "inactive"
        assert EntityStatus.PENDING.value == "pending"
        assert len(EntityStatus) == 3

    def test_waste_type_values(self):
        """Test WasteType enum has correct NOM-052 values."""
        assert WasteType.PELIGROSO.value == "peligroso"
        assert WasteType.ESPECIAL.value == "especial"
        assert WasteType.INERTE.value == "inerte"
        assert WasteType.ORGANICO.value == "organico"
        assert WasteType.RECICLABLE.value == "reciclable"
        assert len(WasteType) == 5

    def test_waste_status_values(self):
        """Test WasteStatus enum has correct values."""
        assert WasteStatus.PENDING.value == "pending"
        assert WasteStatus.ACTIVE.value == "active"
        assert WasteStatus.DISPOSED.value == "disposed"
        assert WasteStatus.ARCHIVED.value == "archived"
        assert len(WasteStatus) == 4


# =============================================================================
# Tests: Employer Model
# =============================================================================

class TestEmployerModel:
    """Tests for Employer model."""

    @pytest.mark.asyncio
    async def test_create_employer(self, db, org):
        """Test creating an employer."""
        employer = Employer(
            organization_id=org.id,
            name="Nuevo Employer",
            rfc="XAA240103HIJ",  # 13 chars valid RFC format
            address="Direccion test",
            status=EntityStatus.ACTIVE,
        )
        db.add(employer)
        await db.commit()
        await db.refresh(employer)

        assert employer.id is not None
        assert employer.name == "Nuevo Employer"
        # H1 FIX: Valid 13-char RFC format
        assert employer.rfc == "XAA240103HIJ"
        assert employer.status == EntityStatus.ACTIVE
        assert employer.created_at is not None

    @pytest.mark.asyncio
    async def test_employer_relationship_org(self, db, org, employer):
        """Test employer-organization relationship."""
        assert employer.organization_id == org.id
        # Refresh to load relationship
        await db.refresh(employer, ["organization"])
        assert employer.organization.id == org.id
        assert employer.organization.name == org.name

    @pytest.mark.asyncio
    async def test_employer_relationship_residues(self, db, employer, residue):
        """Test employer-residue relationship."""
        await db.refresh(employer, ["residues"])
        assert len(employer.residues) == 1
        assert employer.residues[0].id == residue.id

    @pytest.mark.asyncio
    async def test_employer_optional_fields(self, db, org):
        """Test employer optional fields are nullable."""
        employer = Employer(
            organization_id=org.id,
            name="Minimo",
            rfc="XAA240104KLM",  # 13 chars valid RFC
            address="Direccion",
            # Only required fields
        )
        db.add(employer)
        await db.commit()
        await db.refresh(employer)

        assert employer.contact_phone is None
        assert employer.email is None
        assert employer.website is None
        # A5 FIX: extra_data field (SQLAlchemy reserved metadata)
        assert employer.extra_data is None

    @pytest.mark.asyncio
    async def test_employer_repr(self, employer):
        """Test employer string representation."""
        repr_str = repr(employer)
        assert "Employer" in repr_str
        assert employer.name in repr_str
        assert employer.rfc in repr_str

    @pytest.mark.asyncio
    async def test_employer_metadata_json(self, db, org):
        """Test employer extra_data as JSON dict."""
        employer = Employer(
            organization_id=org.id,
            name="With Extra Data",
            rfc="XAA240105NOP",  # 13 chars valid RFC
            address="Addr",
            # A5 FIX: extra_data instead of metadata
            extra_data={"custom_field": "value", "count": 42},
        )
        db.add(employer)
        await db.commit()
        await db.refresh(employer)

        assert employer.extra_data is not None
        assert employer.extra_data["custom_field"] == "value"
        assert employer.extra_data["count"] == 42

    @pytest.mark.asyncio
    async def test_employer_rfc_length(self, db, org):
        """Test employer RFC max 13 chars."""
        employer = Employer(
            organization_id=org.id,
            name="RFC Test",
            rfc="XAA240106QRS",  # 13 chars valid RFC
            address="Addr",
        )
        db.add(employer)
        await db.commit()
        await db.refresh(employer)

        assert len(employer.rfc) <= 13


# =============================================================================
# Tests: Transporter Model
# =============================================================================

class TestTransporterModel:
    """Tests for Transporter model."""

    @pytest.mark.asyncio
    async def test_create_transporter(self, db, org):
        """Test creating a transporter."""
        transporter = Transporter(
            organization_id=org.id,
            name="Transportista Test",
            rfc="XAA240107TUV",  # 13 chars valid RFC
            address="Direccion transportista",
            license_number="LIC-2024-TEST",
            vehicle_plate="XYZ-9999",
            status=EntityStatus.ACTIVE,
        )
        db.add(transporter)
        await db.commit()
        await db.refresh(transporter)

        assert transporter.id is not None
        assert transporter.name == "Transportista Test"
        assert transporter.license_number == "LIC-2024-TEST"
        assert transporter.vehicle_plate == "XYZ-9999"

    @pytest.mark.asyncio
    async def test_transporter_relationship_org(self, db, org, transporter):
        """Test transporter-organization relationship."""
        assert transporter.organization_id == org.id
        await db.refresh(transporter, ["organization"])
        assert transporter.organization.id == org.id

    @pytest.mark.asyncio
    async def test_transporter_relationship_residues(self, db, org, transporter, residue):
        """Test transporter-residue relationship."""
        # Update residue to have transporter
        residue.transporter_id = transporter.id
        await db.commit()
        await db.refresh(transporter, ["residues"])
        assert len(transporter.residues) == 1

    @pytest.mark.asyncio
    async def test_transporter_repr(self, transporter):
        """Test transporter string representation."""
        repr_str = repr(transporter)
        assert "Transporter" in repr_str
        assert transporter.license_number in repr_str

    @pytest.mark.asyncio
    async def test_transporter_updated_at_datetime(self, db, org):
        """C3 FIX: Test transporter.updated_at is DateTime, not String."""
        transporter = Transporter(
            organization_id=org.id,
            name="Updated Test",
            rfc="XAA240108WXY",  # 13 chars valid RFC
            address="Addr",
        )
        db.add(transporter)
        await db.commit()
        await db.refresh(transporter)

        # updated_at should be None initially
        assert transporter.updated_at is None
        
        # Force an update
        transporter.name = "Updated Name 2"
        await db.commit()
        await db.refresh(transporter)
        
        # Now updated_at should be a datetime
        assert transporter.updated_at is not None
        assert isinstance(transporter.updated_at, datetime)


# =============================================================================
# Tests: Residue Model
# =============================================================================

class TestResidueModel:
    """Tests for Residue model."""

    @pytest.mark.asyncio
    async def test_create_residue(self, db, org, employer):
        """Test creating a residue."""
        residue = Residue(
            organization_id=org.id,
            employer_id=employer.id,
            name="Test Residue",
            waste_type=WasteType.ESPECIAL,
            weight_kg=100.0,
            status=WasteStatus.PENDING,
        )
        db.add(residue)
        await db.commit()
        await db.refresh(residue)

        assert residue.id is not None
        assert residue.name == "Test Residue"
        assert residue.waste_type == WasteType.ESPECIAL
        assert residue.weight_kg == 100.0

    @pytest.mark.asyncio
    async def test_residue_relationship_employer(self, db, org, employer, residue):
        """Test residue-employer relationship."""
        assert residue.employer_id == employer.id
        await db.refresh(residue, ["employer"])
        assert residue.employer.id == employer.id

    @pytest.mark.asyncio
    async def test_residue_waste_type_enum(self, db, org, employer):
        """Test residue can use all waste types."""
        for waste_type in WasteType:
            residue = Residue(
                organization_id=org.id,
                employer_id=employer.id,
                name=f"Residue {waste_type.value}",
                waste_type=waste_type,
            )
            db.add(residue)
        await db.commit()

        # Verify all were created
        result = await db.execute(
            select(Residue).where(Residue.organization_id == org.id)
        )
        residues = result.scalars().all()
        assert len(residues) == 5

    @pytest.mark.asyncio
    async def test_residue_repr(self, residue):
        """Test residue string representation."""
        repr_str = repr(residue)
        assert "Residue" in repr_str
        assert residue.name in repr_str
        assert residue.waste_type.value in repr_str

    @pytest.mark.asyncio
    async def test_residue_relationship_organization(self, db, org, employer, residue):
        """C4 FIX: Test residue-organization back_populates."""
        await db.refresh(residue, ["organization"])
        assert residue.organization.id == org.id


# =============================================================================
# Tests: EmployerTransporterLink Model
# =============================================================================

class TestEmployerTransporterLink:
    """Tests for EmployerTransporterLink model."""

    @pytest.mark.asyncio
    async def test_create_link_with_org_id(self, db, org, employer, transporter):
        """C1 FIX: Test link creation requires organization_id."""
        link = EmployerTransporterLink(
            organization_id=org.id,
            employer_id=employer.id,
            transporter_id=transporter.id,
            is_authorized=True,
            notes="Autorizacion de prueba",
        )
        db.add(link)
        await db.commit()
        await db.refresh(link)

        assert link.id is not None
        assert link.organization_id == org.id  # C1: Verify org_id
        assert link.is_authorized is True
        assert link.created_at is not None

    @pytest.mark.asyncio
    async def test_link_relationships(self, db, org, employer, transporter, link):
        """Test link relationships."""
        await db.refresh(link, ["employer", "transporter", "organization"])
        assert link.employer.id == employer.id
        assert link.transporter.id == transporter.id
        assert link.organization.id == org.id

    @pytest.mark.asyncio
    async def test_unauthorized_link(self, db, org):
        """Test creating an unauthorized link."""
        # Create new employer and transporter
        emp = Employer(
            organization_id=org.id,
            name="Emp2",
            rfc="XAA240109ZAB",  # 13 chars valid RFC
            address="Addr2",
        )
        trans = Transporter(
            organization_id=org.id,
            name="Trans2",
            rfc="XAA240110CDE",  # 13 chars valid RFC
            address="Addr3",
        )
        db.add_all([emp, trans])
        await db.flush()

        link = EmployerTransporterLink(
            organization_id=org.id,
            employer_id=emp.id,
            transporter_id=trans.id,
            is_authorized=False,
        )
        db.add(link)
        await db.commit()
        await db.refresh(link)

        assert link.is_authorized is False

    @pytest.mark.asyncio
    async def test_unique_constraint_with_org(self, db, org, employer, transporter, link):
        """Test unique constraint on (org, employer, transporter)."""
        # Try to create duplicate link
        duplicate_link = EmployerTransporterLink(
            organization_id=org.id,
            employer_id=employer.id,
            transporter_id=transporter.id,
        )
        db.add(duplicate_link)

        with pytest.raises(Exception):  # IntegrityError
            await db.commit()

    @pytest.mark.asyncio
    async def test_same_pair_different_orgs(self, db, org, employer, transporter):
        """Test same employer-transporter can exist in different orgs."""
        # Create second org
        org2 = Organization(name="Org2")
        db.add(org2)
        await db.flush()

        # Create employer/transporter in org2
        emp2 = Employer(
            organization_id=org2.id,
            name="Emp3",
            rfc="XBB240111FGH",  # 13 chars valid RFC
            address="Addr4",
        )
        trans2 = Transporter(
            organization_id=org2.id,
            name="Trans3",
            rfc="XBB240112IJK",  # 13 chars valid RFC
            address="Addr5",
        )
        db.add_all([emp2, trans2])
        await db.flush()

        # Link in org2
        link2 = EmployerTransporterLink(
            organization_id=org2.id,
            employer_id=emp2.id,
            transporter_id=trans2.id,
        )
        db.add(link2)
        await db.commit()
        await db.refresh(link2)

        assert link2.id is not None
        assert link2.organization_id == org2.id


# =============================================================================
# Tests: Multi-tenancy Isolation
# =============================================================================

class TestMultiTenancyIsolation:
    """Tests for tenant isolation on domain models."""

    @pytest.mark.asyncio
    async def test_employer_org_isolation(self, db, org, employer):
        """Test employer belongs to correct organization."""
        # employer fixture already creates one in org
        # Now create second org with another employer
        org2 = Organization(name="Org 2")
        db.add(org2)
        await db.flush()

        employer2 = Employer(
            organization_id=org2.id,
            name="Employer Org2",
            rfc="XBB240113LMN",  # 13 chars valid RFC
            address="Addr",
        )
        db.add(employer2)
        await db.commit()

        # Query should only return employers in original org
        result = await db.execute(
            select(Employer).where(Employer.organization_id == org.id)
        )
        employers = result.scalars().all()
        # Should find only the employer from fixture, not employer2
        assert len(employers) >= 1
        for emp in employers:
            assert emp.organization_id == org.id

    @pytest.mark.asyncio
    async def test_transporter_org_isolation(self, db, org):
        """Test transporter belongs to correct organization."""
        org2 = Organization(name="Org 3")
        db.add(org2)
        await db.flush()

        trans = Transporter(
            organization_id=org2.id,
            name="Trans Org2",
            rfc="XBB240114OPQ",  # 13 chars valid RFC
            address="Addr",
        )
        db.add(trans)
        await db.commit()

        result = await db.execute(
            select(Transporter).where(Transporter.organization_id == org.id)
        )
        transporters = result.scalars().all()
        assert len(transporters) == 0

    @pytest.mark.asyncio
    async def test_residue_inherits_org(self, db, org, employer):
        """Test residue organization_id matches employer."""
        residue = Residue(
            organization_id=org.id,
            employer_id=employer.id,
            name="Residuo test",
            waste_type=WasteType.INERTE,
        )
        db.add(residue)
        await db.commit()

        # Both should have same org
        assert residue.organization_id == employer.organization_id

    @pytest.mark.asyncio
    async def test_link_org_isolation(self, db, org):
        """Test link queries filter by organization_id."""
        org2 = Organization(name="Org 4")
        db.add(org2)
        await db.flush()

        emp = Employer(
            organization_id=org2.id,
            name="Emp4",
            rfc="XBB240115RST",  # 13 chars valid RFC
            address="Addr",
        )
        trans = Transporter(
            organization_id=org2.id,
            name="Trans4",
            rfc="XBB240116UVW",  # 13 chars valid RFC
            address="Addr",
        )
        db.add_all([emp, trans])
        await db.flush()

        link = EmployerTransporterLink(
            organization_id=org2.id,
            employer_id=emp.id,
            transporter_id=trans.id,
        )
        db.add(link)
        await db.commit()

        # Query for org1 should not include org2's link
        result = await db.execute(
            select(EmployerTransporterLink).where(
                EmployerTransporterLink.organization_id == org.id
            )
        )
        links = result.scalars().all()
        assert len(links) == 0


# =============================================================================
# Tests: Schema Validation (Pydantic)
# =============================================================================

class TestDomainSchemas:
    """Tests for Pydantic schemas validation."""

    def test_employer_create_schema_valid(self):
        """Test valid employer creation schema."""
        from app.schemas.domain import EmployerCreate
        
        # H1 FIX: Valid 13-char RFC format
        data = EmployerCreate(
            name="Test Employer",
            rfc="XAA240117XYZ",  # 13 chars valid RFC
            address="Test Address 123",
            email="test@example.com",
        )
        assert data.name == "Test Employer"
        assert data.status.value == "active"

    def test_employer_create_schema_invalid_rfc(self):
        """Test employer rejects invalid RFC format."""
        from app.schemas.domain import EmployerCreate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            EmployerCreate(
                name="Test",
                rfc="INVALID",  # Wrong format (too short)
                address="Address",
            )
        # Check for either pydantic message or our custom validator
        error_str = str(exc_info.value)
        assert "string_too_short" in error_str or "RFC" in error_str

    def test_employer_create_schema_rfc_too_short(self):
        """Test employer rejects RFC too short."""
        from app.schemas.domain import EmployerCreate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            EmployerCreate(
                name="Test",
                rfc="XAXX0101",  # Only 8 chars
                address="Address",
            )

    def test_employer_email_validation(self):
        """A3 FIX: Test EmailStr validation."""
        from app.schemas.domain import EmployerCreate
        from pydantic import ValidationError
        
        # Valid email
        data = EmployerCreate(
            name="Test",
            rfc="XAA240118AAA",  # 13 chars valid RFC
            address="Addr",
            email="valid@example.com",
        )
        assert data.email == "valid@example.com"
        
        # Invalid email
        with pytest.raises(ValidationError):
            EmployerCreate(
                name="Test",
                rfc="XAA240119BBB",  # 13 chars valid RFC
                address="Addr",
                email="not-an-email",
            )

    def test_residue_create_schema_valid(self):
        """Test valid residue creation schema."""
        from app.schemas.domain import ResidueCreate, WasteTypeEnum, WasteStatusEnum
        
        data = ResidueCreate(
            name="Baterias",
            waste_type=WasteTypeEnum.PELIGROSO,
            employer_id=1,
            weight_kg=100.5,
        )
        assert data.waste_type == WasteTypeEnum.PELIGROSO
        assert data.weight_kg == 100.5

    def test_transporter_create_schema_valid(self):
        """Test valid transporter creation schema."""
        from app.schemas.domain import TransporterCreate, EntityStatusEnum
        
        # H1 FIX: Valid 13-char RFC format
        data = TransporterCreate(
            name="Transportes Rapidos",
            rfc="XAA240120CCC",  # 13 chars valid RFC
            address="Av. Principal 456",
            license_number="SEM-2024-001",
            vehicle_plate="ABC-1234",
        )
        assert data.status == EntityStatusEnum.ACTIVE

    def test_residue_update_schema_partial(self):
        """Test partial update schema accepts None for optional fields."""
        from app.schemas.domain import ResidueUpdate, WasteStatusEnum
        
        data = ResidueUpdate(
            name="Updated Name",
            status=WasteStatusEnum.ARCHIVED,
        )
        assert data.name == "Updated Name"
        assert data.waste_type is None  # Not required in update
        assert data.weight_kg is None

    def test_link_response_includes_org_id(self):
        """C1 FIX: Test link response includes organization_id."""
        from app.schemas.domain import EmployerTransporterLinkResponse
        from datetime import datetime
        
        data = EmployerTransporterLinkResponse(
            id=1,
            organization_id=5,
            employer_id=10,
            transporter_id=20,
            is_authorized=True,
            created_at=datetime.now(),
        )
        assert data.organization_id == 5

    def test_extra_data_as_dict(self):
        """A5 FIX: Test extra_data field accepts dict."""
        from app.schemas.domain import EmployerCreate
        
        # H1 FIX: Valid 13-char RFC format
        data = EmployerCreate(
            name="Test",
            rfc="XAA240121DDD",  # 13 chars valid RFC
            address="Addr",
            # A5 FIX: extra_data instead of metadata
            extra_data={"key": "value", "number": 42},
        )
        assert data.extra_data["key"] == "value"
        assert data.extra_data["number"] == 42


# =============================================================================
# Tests: H2 - archived_at soft delete
# =============================================================================

class TestArchivedAtSoftDelete:
    """Tests for H2: archived_at soft delete field."""

    @pytest.mark.asyncio
    async def test_employer_archived_at_field(self, db, org):
        """Test employer has archived_at field with DateTime."""
        from datetime import datetime
        employer = Employer(
            organization_id=org.id,
            name="Archive Test",
            rfc="XAA240122EEE",
            address="Addr",
        )
        db.add(employer)
        await db.commit()
        await db.refresh(employer)

        # Initially None
        assert employer.archived_at is None
        
        # Set archived_at
        now = datetime.now(timezone.utc)
        employer.archived_at = now
        await db.commit()
        await db.refresh(employer)
        
        assert employer.archived_at is not None
        assert isinstance(employer.archived_at, datetime)

    @pytest.mark.asyncio
    async def test_transporter_archived_at_field(self, db, org):
        """Test transporter has archived_at field with DateTime."""
        from datetime import datetime
        trans = Transporter(
            organization_id=org.id,
            name="Archive Trans Test",
            rfc="XAA240123FFF",
            address="Addr",
        )
        db.add(trans)
        await db.commit()
        await db.refresh(trans)

        assert trans.archived_at is None
        
        now = datetime.now(timezone.utc)
        trans.archived_at = now
        await db.commit()
        await db.refresh(trans)
        
        assert trans.archived_at is not None
        assert isinstance(trans.archived_at, datetime)


# =============================================================================
# Tests: H1 - RFC with Ñ support
# =============================================================================

class TestRFCWithEnye:
    """Tests for H1: RFC pattern supporting Ñ."""

    def test_rfc_with_enye_valid(self):
        """Test RFC validation accepts Ñ in first positions."""
        from app.schemas.domain import EmployerCreate
        
        # Valid RFC with Ñ
        data = EmployerCreate(
            name="RFC Enye Test",
            rfc="ÑAA240124GGG",  # Ñ is valid at start
            address="Test Address",
        )
        assert data.rfc == "ÑAA240124GGG"

    def test_rfc_with_ampersand_valid(self):
        """Test RFC validation accepts & (used in some companies)."""
        from app.schemas.domain import EmployerCreate
        
        # Valid RFC with &
        data = EmployerCreate(
            name="RFC Ampersand Test",
            rfc="A&B240125HHH",  # & is valid
            address="Test Address",
        )
        assert data.rfc == "A&B240125HHH"


# =============================================================================
# FASE 4A: Waste/Audit/Billing Tests
# =============================================================================


class TestNewEnums4A:
    """Tests for new enums added in Phase 4A."""

    def test_movement_status_values(self):
        """Test MovementStatus enum has correct values."""
        from app.models import MovementStatus
        
        assert MovementStatus.PENDING.value == "pending"
        assert MovementStatus.IN_REVIEW.value == "in_review"
        assert MovementStatus.VALIDATED.value == "validated"
        assert MovementStatus.REJECTED.value == "rejected"
        assert MovementStatus.EXCEPTION.value == "exception"
        assert len(MovementStatus) == 5

    def test_alert_severity_values(self):
        """Test AlertSeverity enum has correct values."""
        from app.models import AlertSeverity
        
        assert AlertSeverity.LOW.value == "low"
        assert AlertSeverity.MEDIUM.value == "medium"
        assert AlertSeverity.HIGH.value == "high"
        assert AlertSeverity.CRITICAL.value == "critical"
        assert len(AlertSeverity) == 4

    def test_alert_status_values(self):
        """Test AlertStatus enum has correct values."""
        from app.models import AlertStatus
        
        assert AlertStatus.OPEN.value == "open"
        assert AlertStatus.ACKNOWLEDGED.value == "acknowledged"
        assert AlertStatus.RESOLVED.value == "resolved"
        assert AlertStatus.DISMISSED.value == "dismissed"
        assert len(AlertStatus) == 4

    def test_subscription_status_values(self):
        """Test SubscriptionStatus enum has correct values."""
        from app.models import SubscriptionStatus
        
        assert SubscriptionStatus.ACTIVE.value == "active"
        assert SubscriptionStatus.PAUSED.value == "paused"
        assert SubscriptionStatus.CANCELLED.value == "cancelled"
        assert SubscriptionStatus.PAST_DUE.value == "past_due"
        assert len(SubscriptionStatus) == 4

    def test_billing_plan_code_values(self):
        """Test BillingPlanCode enum has correct values."""
        from app.models import BillingPlanCode
        
        assert BillingPlanCode.FREE.value == "free"
        assert BillingPlanCode.PRO.value == "pro"
        assert BillingPlanCode.ENTERPRISE.value == "enterprise"
        assert len(BillingPlanCode) == 3

    def test_audit_log_result_values(self):
        """Test AuditLogResult enum has correct values."""
        from app.models import AuditLogResult
        
        assert AuditLogResult.SUCCESS.value == "success"
        assert AuditLogResult.FAILURE.value == "failure"
        assert AuditLogResult.PARTIAL.value == "partial"
        assert len(AuditLogResult) == 3


class TestAuditLogModel:
    """Tests for AuditLog model (Phase 4A)."""

    @pytest.mark.asyncio
    async def test_create_audit_log(self, db, org):
        """Test creating an audit log entry."""
        from app.models import AuditLog, AuditLogResult
        
        log = AuditLog(
            organization_id=org.id,
            user_id=1,
            action="CREATE",
            resource_type="employer",
            resource_id="123",
            result=AuditLogResult.SUCCESS,
            payload_json={"key": "value"},
            ip_address="192.168.1.1",
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)

        assert log.id is not None
        assert log.organization_id == org.id
        assert log.action == "CREATE"
        assert log.result == AuditLogResult.SUCCESS
        assert log.timestamp is not None

    @pytest.mark.asyncio
    async def test_audit_log_pii_redaction_payload(self, db, org):
        """Test audit log stores PII-redacted payload."""
        from app.models import AuditLog
        
        # Simulating redacted payload (email should be masked before storing)
        log = AuditLog(
            organization_id=org.id,
            action="LOGIN",
            resource_type="session",
            payload_json={
                "email": "t***@***.com",  # Pre-redacted
                "ip": "192.168.1.1",
            },
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)

        assert log.payload_json["email"] == "t***@***.com"  # Already redacted
        assert "raw_password" not in str(log.payload_json)

    @pytest.mark.asyncio
    async def test_audit_log_multi_tenant_isolation(self, db, org):
        """Test audit log enforces tenant isolation."""
        from app.models import AuditLog
        
        # Create org2
        org2 = Organization(name="Org2")
        db.add(org2)
        await db.flush()

        # Create logs in different orgs
        log1 = AuditLog(
            organization_id=org.id,
            action="TEST",
            resource_type="test",
        )
        log2 = AuditLog(
            organization_id=org2.id,
            action="TEST",
            resource_type="test",
        )
        db.add_all([log1, log2])
        await db.commit()

        # Query for org1 should NOT include org2's log
        result = await db.execute(
            select(AuditLog).where(AuditLog.organization_id == org.id)
        )
        logs = result.scalars().all()
        assert len(logs) == 1
        assert logs[0].organization_id == org.id


class TestBillingPlanModel:
    """Tests for BillingPlan model (Phase 4A)."""

    @pytest.mark.asyncio
    async def test_create_billing_plan(self, db):
        """Test creating a billing plan."""
        from app.models import BillingPlan, BillingPlanCode
        
        plan = BillingPlan(
            code=BillingPlanCode.PRO,
            name="Pro Plan",
            description="Professional tier",
            price_usd_cents=4900,  # $49.00
            doc_limit=1000,
            doc_limit_period="monthly",
            features_json={"ai_analysis": True, "priority_support": True},
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        assert plan.id is not None
        assert plan.code == BillingPlanCode.PRO
        assert plan.price_usd_cents == 4900
        assert plan.features_json["ai_analysis"] is True

    @pytest.mark.asyncio
    async def test_billing_plan_unlimited_doc_limit(self, db):
        """Test billing plan with unlimited documents (doc_limit=0)."""
        from app.models import BillingPlan, BillingPlanCode
        
        plan = BillingPlan(
            code=BillingPlanCode.ENTERPRISE,
            name="Enterprise",
            price_usd_cents=19900,
            doc_limit=0,  # Unlimited
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        assert plan.doc_limit == 0  # Unlimited

    @pytest.mark.asyncio
    async def test_billing_plan_free_tier(self, db):
        """Test free tier billing plan."""
        from app.models import BillingPlan, BillingPlanCode
        
        plan = BillingPlan(
            code=BillingPlanCode.FREE,
            name="Free",
            description="Free tier",
            price_usd_cents=0,
            doc_limit=100,
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        assert plan.price_usd_cents == 0
        assert plan.doc_limit == 100


class TestSubscriptionModel:
    """Tests for Subscription model (Phase 4A)."""

    @pytest.mark.asyncio
    async def test_create_subscription(self, db, org):
        """Test creating a subscription."""
        from app.models import Subscription, BillingPlan, SubscriptionStatus, BillingPlanCode
        
        # Create plan first
        plan = BillingPlan(
            code=BillingPlanCode.PRO,
            name="Pro",
            price_usd_cents=4900,
            doc_limit=1000,
        )
        db.add(plan)
        await db.flush()

        # Create subscription
        sub = Subscription(
            organization_id=org.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            stripe_customer_id="cus_test123",
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)

        assert sub.id is not None
        assert sub.organization_id == org.id
        assert sub.status == SubscriptionStatus.ACTIVE
        assert sub.started_at is not None

    @pytest.mark.asyncio
    async def test_subscription_unique_per_org(self, db, org):
        """Test only one subscription per organization."""
        from app.models import Subscription, BillingPlan, BillingPlanCode, SubscriptionStatus
        
        plan = BillingPlan(code=BillingPlanCode.FREE, name="Free", price_usd_cents=0)
        db.add(plan)
        await db.flush()

        # First subscription
        sub1 = Subscription(
            organization_id=org.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
        )
        db.add(sub1)
        await db.commit()

        # Try duplicate (should fail unique constraint)
        sub2 = Subscription(
            organization_id=org.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
        )
        db.add(sub2)
        with pytest.raises(Exception):  # IntegrityError
            await db.commit()


class TestUsageCycleModel:
    """Tests for UsageCycle model (Phase 4A)."""

    @pytest.mark.asyncio
    async def test_create_usage_cycle(self, db, org):
        """Test creating a usage cycle."""
        from app.models import UsageCycle, Subscription, BillingPlan, BillingPlanCode
        
        # Create plan and subscription
        plan = BillingPlan(code=BillingPlanCode.PRO, name="Pro", price_usd_cents=4900)
        db.add(plan)
        await db.flush()
        
        sub = Subscription(
            organization_id=org.id,
            plan_id=plan.id,
        )
        db.add(sub)
        await db.flush()

        # Create usage cycle
        cycle = UsageCycle(
            subscription_id=sub.id,
            month_year="2026-04",
            docs_used=150,
            docs_limit=1000,
        )
        db.add(cycle)
        await db.commit()
        await db.refresh(cycle)

        assert cycle.id is not None
        assert cycle.month_year == "2026-04"
        assert cycle.docs_used == 150
        assert cycle.is_locked is False

    @pytest.mark.asyncio
    async def test_usage_cycle_lock(self, db, org):
        """Test usage cycle can be locked after period ends."""
        from app.models import UsageCycle, Subscription, BillingPlan, BillingPlanCode
        
        plan = BillingPlan(code=BillingPlanCode.FREE, name="Free", doc_limit=100)
        db.add(plan)
        await db.flush()
        
        sub = Subscription(organization_id=org.id, plan_id=plan.id)
        db.add(sub)
        await db.flush()

        cycle = UsageCycle(
            subscription_id=sub.id,
            month_year="2026-03",
            docs_used=100,
            docs_limit=100,
            is_locked=True,  # Period ended
        )
        db.add(cycle)
        await db.commit()
        await db.refresh(cycle)

        assert cycle.is_locked is True

    @pytest.mark.asyncio
    async def test_usage_cycle_unique_month(self, db, org):
        """Test unique constraint on subscription + month_year."""
        from app.models import UsageCycle, Subscription, BillingPlan, BillingPlanCode
        
        plan = BillingPlan(code=BillingPlanCode.FREE, name="Free")
        db.add(plan)
        await db.flush()
        
        sub = Subscription(organization_id=org.id, plan_id=plan.id)
        db.add(sub)
        await db.flush()

        cycle1 = UsageCycle(subscription_id=sub.id, month_year="2026-04")
        db.add(cycle1)
        await db.commit()

        # Duplicate month should fail
        cycle2 = UsageCycle(subscription_id=sub.id, month_year="2026-04")
        db.add(cycle2)
        with pytest.raises(Exception):
            await db.commit()


class TestLegalAlertModel:
    """Tests for LegalAlert model (Phase 4A)."""

    @pytest.mark.asyncio
    async def test_create_legal_alert(self, db, org):
        """Test creating a legal alert."""
        from app.models import LegalAlert, AlertSeverity, AlertStatus
        
        alert = LegalAlert(
            organization_id=org.id,
            norma="NOM-052",
            title="Residuo peligroso sin manifiesto",
            description="Se detecto residuo PELIGROSO sin documento de transporte",
            severity=AlertSeverity.HIGH,
            status=AlertStatus.OPEN,
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)

        assert alert.id is not None
        assert alert.norma == "NOM-052"
        assert alert.severity == AlertSeverity.HIGH
        assert alert.status == AlertStatus.OPEN

    @pytest.mark.asyncio
    async def test_legal_alert_resolve(self, db, org):
        """Test resolving a legal alert."""
        from datetime import datetime, timezone
        
        alert = LegalAlert(
            organization_id=org.id,
            norma="LFPDPPP",
            title="Aviso de privacidad pendiente",
            severity=AlertSeverity.MEDIUM,  # Use correct enum for severity
            status=AlertStatus.OPEN,        # Use correct enum for status
        )
        db.add(alert)
        await db.commit()
        
        # Resolve
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolution_notes = "Aviso publicado en el sitio web"
        await db.commit()
        await db.refresh(alert)

        assert alert.status == AlertStatus.RESOLVED
        assert alert.resolved_at is not None
        assert alert.resolution_notes is not None

    @pytest.mark.asyncio
    async def test_legal_alert_multi_tenant(self, db, org):
        """Test legal alerts are tenant-isolated."""
        from app.models import LegalAlert
        
        # Create second org
        org2 = Organization(name="Org2")
        db.add(org2)
        await db.flush()

        alert1 = LegalAlert(organization_id=org.id, norma="NOM-052", title="Alert 1")
        alert2 = LegalAlert(organization_id=org2.id, norma="NOM-052", title="Alert 2")
        db.add_all([alert1, alert2])
        await db.commit()

        # Query for org1 should only return alert1
        result = await db.execute(
            select(LegalAlert).where(LegalAlert.organization_id == org.id)
        )
        alerts = result.scalars().all()
        assert len(alerts) == 1
        assert alerts[0].title == "Alert 1"


class TestWasteMovementModel:
    """Tests for WasteMovement model (Phase 4A)."""

    @pytest.mark.asyncio
    async def test_create_waste_movement(self, db, org):
        """Test creating a waste movement."""
        from app.models import WasteMovement, MovementStatus
        
        movement = WasteMovement(
            organization_id=org.id,
            manifest_number="MAN-2026-001",
            movement_type="TRANSPORTE",
            quantity=500.0,
            unit="kg",
            status=MovementStatus.PENDING,
            confidence_score=0.95,
        )
        db.add(movement)
        await db.commit()
        await db.refresh(movement)

        assert movement.id is not None
        assert movement.manifest_number == "MAN-2026-001"
        assert movement.status == MovementStatus.PENDING
        assert movement.is_immutable is False

    @pytest.mark.asyncio
    async def test_waste_movement_immutable(self, db, org):
        """Test waste movement can be marked immutable after validation."""
        from app.models import WasteMovement, MovementStatus
        
        movement = WasteMovement(
            organization_id=org.id,
            manifest_number="MAN-2026-002",
            status=MovementStatus.VALIDATED,
            is_immutable=True,  # Once validated, cannot be modified
        )
        db.add(movement)
        await db.commit()
        await db.refresh(movement)

        assert movement.is_immutable is True
        assert movement.status == MovementStatus.VALIDATED

    @pytest.mark.asyncio
    async def test_waste_movement_multi_tenant(self, db, org):
        """Test waste movements are tenant-isolated."""
        from app.models import WasteMovement
        
        org2 = Organization(name="Org2")
        db.add(org2)
        await db.flush()

        mv1 = WasteMovement(organization_id=org.id, manifest_number="MAN-A-001")
        mv2 = WasteMovement(organization_id=org2.id, manifest_number="MAN-B-001")
        db.add_all([mv1, mv2])
        await db.commit()

        # Org1 should only see mv1
        result = await db.execute(
            select(WasteMovement).where(WasteMovement.organization_id == org.id)
        )
        movements = result.scalars().all()
        assert len(movements) == 1
        assert movements[0].manifest_number == "MAN-A-001"


class TestBillingSchemas4A:
    """Tests for Phase 4A Pydantic schemas."""

    def test_audit_log_create_schema(self):
        """Test AuditLogCreate schema validation."""
        from app.schemas.domain import AuditLogCreate, AuditLogResultEnum
        
        data = AuditLogCreate(
            organization_id=1,
            action="LOGIN",
            resource_type="session",
            result=AuditLogResultEnum.SUCCESS,
        )
        assert data.action == "LOGIN"
        assert data.result == AuditLogResultEnum.SUCCESS

    def test_billing_plan_create_schema(self):
        """Test BillingPlanCreate schema validation."""
        from app.schemas.domain import BillingPlanCreate, BillingPlanCodeEnum
        
        data = BillingPlanCreate(
            code=BillingPlanCodeEnum.PRO,
            name="Pro Plan",
            price_usd_cents=4900,
            doc_limit=1000,
        )
        assert data.code == BillingPlanCodeEnum.PRO
        assert data.price_usd_cents == 4900

    def test_subscription_create_schema(self):
        """Test SubscriptionCreate schema validation."""
        from app.schemas.domain import SubscriptionCreate, SubscriptionStatusEnum
        
        data = SubscriptionCreate(
            organization_id=1,
            plan_id=1,
            status=SubscriptionStatusEnum.ACTIVE,
        )
        assert data.status == SubscriptionStatusEnum.ACTIVE

    def test_usage_cycle_create_schema(self):
        """Test UsageCycleCreate schema with YYYY-MM format."""
        from app.schemas.domain import UsageCycleCreate
        
        data = UsageCycleCreate(
            subscription_id=1,
            month_year="2026-04",
            docs_used=150,
            docs_limit=1000,
        )
        assert data.month_year == "2026-04"

    def test_usage_cycle_invalid_month_format(self):
        """Test UsageCycleCreate rejects invalid month format."""
        from app.schemas.domain import UsageCycleCreate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            UsageCycleCreate(
                subscription_id=1,
                month_year="04-2026",  # Wrong format
            )

    def test_legal_alert_create_schema(self):
        """Test LegalAlertCreate schema validation."""
        from app.schemas.domain import LegalAlertCreate, AlertSeverityEnum, AlertStatusEnum
        
        data = LegalAlertCreate(
            organization_id=1,
            norma="NOM-052",
            title="Alert Test",
            severity=AlertSeverityEnum.HIGH,
            status=AlertStatusEnum.OPEN,
        )
        assert data.norma == "NOM-052"
        assert data.severity == AlertSeverityEnum.HIGH