"""
Tests para FIX 5B-FIX-1: Audit trail y UniqueConstraint

Verifica:
1. Middleware extrae resource_type="waste" no "v1" para rutas /api/v1/*
2. UniqueConstraint en WasteMovement (org_id + manifest_number + date)
3. Auditoría explícita registra actor, org, acción, resultado, payload
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock

from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError

from app.models import (
    User,
    Organization,
    Membership,
    WasteMovement,
    MovementStatus,
    UserRole,
)
from app.api.middleware.audit import extract_path_pattern


# =============================================================================
# Fixtures locales (copiados de test_waste_api.py)
# =============================================================================

@pytest.fixture
async def org(db) -> Organization:
    """Create a test organization."""
    org = Organization(name="Test Org Audit")
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@pytest.fixture
async def other_org(db) -> Organization:
    """Create a second test organization for cross-tenant tests."""
    org = Organization(name="Other Org Audit")
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@pytest.fixture
async def owner_user(db, org) -> User:
    """Create a test user with owner role."""
    user = User(
        email="owner@audit.test",
        hashed_password="hashed",
        full_name="Owner User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    membership = Membership(
        user_id=user.id,
        organization_id=org.id,
        role=UserRole.OWNER,
    )
    db.add(membership)
    await db.commit()
    
    return user


@pytest.fixture
async def waste_movement(db, org) -> WasteMovement:
    """Create a test waste movement."""
    movement = WasteMovement(
        organization_id=org.id,
        manifest_number="MAN-AUDIT-001",
        status=MovementStatus.PENDING,
        is_immutable=False,
    )
    db.add(movement)
    await db.commit()
    await db.refresh(movement)
    return movement


# =============================================================================
# Test: extract_path_pattern CORRECCIÓN
# =============================================================================

class TestExtractPathPattern:
    """Tests para verificar que el middleware extrae correctamente el resource type."""

    def test_extract_v1_waste_path(self):
        """Ruta /api/v1/waste/123 debe extraer 'waste' no 'v1'."""
        result = extract_path_pattern("/api/v1/waste/123")
        assert result == "waste", f"Expected 'waste', got '{result}'"

    def test_extract_v1_waste_list(self):
        """Ruta /api/v1/waste debe extraer 'waste'."""
        result = extract_path_pattern("/api/v1/waste")
        assert result == "waste"

    def test_extract_v1_waste_stats(self):
        """Ruta /api/v1/waste/stats debe extraer 'waste'."""
        result = extract_path_pattern("/api/v1/waste/stats")
        assert result == "waste"

    def test_extract_v1_waste_archive(self):
        """Ruta /api/v1/waste/123/archive debe extraer 'waste'."""
        result = extract_path_pattern("/api/v1/waste/123/archive")
        assert result == "waste"

    def test_extract_legacy_api_path(self):
        """Ruta /api/employers/123 sigue extrayendo 'employer'."""
        result = extract_path_pattern("/api/employers/123")
        assert result == "employer"

    def test_extract_v1_billing_path(self):
        """Ruta /api/v1/billing/plans debe extraer 'billing'."""
        result = extract_path_pattern("/api/v1/billing/plans")
        assert result == "billing"

    def test_extract_v1_orgs_path(self):
        """Ruta /api/v1/orgs/me debe extraer 'org'."""
        result = extract_path_pattern("/api/v1/orgs/me")
        assert result == "org"


# =============================================================================
# Test: UniqueConstraint en WasteMovement
# =============================================================================

class TestWasteMovementUniqueConstraint:
    """Tests para verificar la unique constraint en WasteMovement."""

    @pytest.mark.asyncio
    async def test_duplicate_manifest_same_org_same_date_rejected(
        self,
        db,
        org,
    ):
        """No puede haber dos movimientos con mismo manifest/fecha para misma org."""
        date = datetime.now(timezone.utc)
        
        # Crear primer movimiento
        m1 = WasteMovement(
            organization_id=org.id,
            manifest_number="MAN-DUP-001",
            date=date,
            status=MovementStatus.PENDING,
        )
        db.add(m1)
        await db.commit()
        
        # Intentar crear segundo con mismo manifest/fecha
        m2 = WasteMovement(
            organization_id=org.id,
            manifest_number="MAN-DUP-001",
            date=date,
            status=MovementStatus.PENDING,
        )
        db.add(m2)
        
        with pytest.raises(IntegrityError):
            await db.commit()

    @pytest.mark.asyncio
    async def test_same_manifest_different_date_allowed(
        self,
        db,
        org,
    ):
        """Mismo manifest pero diferente fecha debe ser permitido."""
        date1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        date2 = datetime(2026, 1, 2, tzinfo=timezone.utc)
        
        m1 = WasteMovement(
            organization_id=org.id,
            manifest_number="MAN-DATE-001",
            date=date1,
            status=MovementStatus.PENDING,
        )
        db.add(m1)
        await db.commit()
        
        m2 = WasteMovement(
            organization_id=org.id,
            manifest_number="MAN-DATE-001",
            date=date2,
            status=MovementStatus.PENDING,
        )
        db.add(m2)
        
        # No debe lanzar error
        await db.commit()
        
        # Verificar que ambos existen
        result = await db.execute(
            select(WasteMovement).where(
                and_(
                    WasteMovement.organization_id == org.id,
                    WasteMovement.manifest_number == "MAN-DATE-001",
                )
            )
        )
        movements = result.scalars().all()
        assert len(movements) == 2

    @pytest.mark.asyncio
    async def test_same_manifest_different_org_allowed(
        self,
        db,
        org,
        other_org,
    ):
        """Mismo manifest pero diferente org debe ser permitido."""
        date = datetime.now(timezone.utc)
        
        m1 = WasteMovement(
            organization_id=org.id,
            manifest_number="MAN-ORG-001",
            date=date,
            status=MovementStatus.PENDING,
        )
        db.add(m1)
        await db.commit()
        
        m2 = WasteMovement(
            organization_id=other_org.id,
            manifest_number="MAN-ORG-001",
            date=date,
            status=MovementStatus.PENDING,
        )
        db.add(m2)
        await db.commit()
        
        # Verificar que ambos existen
        result = await db.execute(
            select(WasteMovement).where(
                WasteMovement.manifest_number == "MAN-ORG-001"
            )
        )
        movements = result.scalars().all()
        assert len(movements) == 2


# =============================================================================
# Test: Auditoría explícita en waste.py (usando mocks)
# =============================================================================

class TestWasteMovementAudit:
    """Tests para verificar que se llama a record_audit_event en mutaciones."""

    @pytest.mark.asyncio
    async def test_create_calls_audit(
        self,
        client,
        db,
        owner_user,
        org,
    ):
        """Create debe llamar a record_audit_event."""
        from app.core.tokens import create_access_token
        from unittest.mock import patch, AsyncMock
        
        token = create_access_token(owner_user.id, org.id, "owner")
        
        with patch('app.api.v1.waste.record_audit_event', new_callable=AsyncMock) as mock_audit:
            response = await client.post(
                "/api/v1/waste",
                json={
                    "manifest_number": "MAN-AUDIT-001",
                    "quantity": 100.0,
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            
            assert response.status_code == 201
            
            # Verificar que se llamó a record_audit_event
            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args.kwargs
            
            assert call_kwargs["action"] == "create"
            assert call_kwargs["resource_type"] == "waste_movement"
            assert call_kwargs["organization_id"] == org.id
            assert call_kwargs["user_id"] == owner_user.id
            assert "MAN-AUDIT-001" in str(call_kwargs.get("metadata", {}))

    @pytest.mark.asyncio
    async def test_update_calls_audit(
        self,
        client,
        db,
        owner_user,
        org,
        waste_movement,
    ):
        """Update debe llamar a record_audit_event con changed_fields."""
        from app.core.tokens import create_access_token
        from unittest.mock import patch, AsyncMock
        
        token = create_access_token(owner_user.id, org.id, "owner")
        
        with patch('app.api.v1.waste.record_audit_event', new_callable=AsyncMock) as mock_audit:
            response = await client.patch(
                f"/api/v1/waste/{waste_movement.id}",
                json={
                    "quantity": 200.0,
                    "status": "in_review",
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            
            assert response.status_code == 200
            
            # Verificar que se llamó a record_audit_event
            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args.kwargs
            
            assert call_kwargs["action"] == "update"
            assert call_kwargs["resource_type"] == "waste_movement"
            assert call_kwargs["resource_id"] == str(waste_movement.id)

    @pytest.mark.asyncio
    async def test_archive_calls_audit(
        self,
        client,
        db,
        owner_user,
        org,
        waste_movement,
    ):
        """Archive debe llamar a record_audit_event con acción ARCHIVE (no DELETE)."""
        from app.core.tokens import create_access_token
        from unittest.mock import patch, AsyncMock
        from app.core.audit import AuditAction
        
        token = create_access_token(owner_user.id, org.id, "owner")
        
        with patch('app.api.v1.waste.record_audit_event', new_callable=AsyncMock) as mock_audit:
            response = await client.post(
                f"/api/v1/waste/{waste_movement.id}/archive",
                headers={"Authorization": f"Bearer {token}"},
            )
            
            assert response.status_code == 200
            
            # Verificar que se llamó a record_audit_event con acción ARCHIVE
            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args.kwargs
            
            assert call_kwargs["action"] == AuditAction.ARCHIVE, \
                f"Expected AuditAction.ARCHIVE, got {call_kwargs['action']}"
            assert call_kwargs["resource_type"] == "waste_movement"
            assert call_kwargs["resource_id"] == str(waste_movement.id)
            assert call_kwargs["metadata"].get("action") == "soft_delete"
