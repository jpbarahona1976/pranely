"""
PRANELY - Test Suite for Multi-Org Tenant Isolation

Tests that verify correct tenant isolation when a user belongs to multiple organizations.
DT-001 Fix: org_id from JWT must govern tenant context, not first membership.

Uses fixtures from conftest.py for database session management with automatic table truncation.
"""
import pytest
from datetime import datetime, timezone
from typing import AsyncGenerator

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tokens import create_access_token
from app.models import User, Organization, Membership, UserRole, Employer


# =============================================================================
# Fixtures
# =============================================================================
# Note: db_session fixture is provided by conftest.py
# It includes automatic table truncation after each test


@pytest.fixture
async def org_a(db_session: AsyncSession) -> Organization:
    """Create organization A."""
    org = Organization(name="Org A", legal_name="Organization A S.A.")
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def org_b(db_session: AsyncSession) -> Organization:
    """Create organization B."""
    org = Organization(name="Org B", legal_name="Organization B S.A.")
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def shared_user(db_session: AsyncSession) -> User:
    """Create a user that belongs to both organizations."""
    user = User(
        email="shared@example.com",
        hashed_password="$argon2id$v=19$m=65536,t=3,p=4$test",
        full_name="Shared User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def membership_a(
    db_session: AsyncSession,
    shared_user: User,
    org_a: Organization
) -> Membership:
    """Create membership for user in Org A."""
    membership = Membership(
        user_id=shared_user.id,
        organization_id=org_a.id,
        role=UserRole.OWNER,
    )
    db_session.add(membership)
    await db_session.commit()
    await db_session.refresh(membership)
    return membership


@pytest.fixture
async def membership_b(
    db_session: AsyncSession,
    shared_user: User,
    org_b: Organization
) -> Membership:
    """Create membership for user in Org B."""
    membership = Membership(
        user_id=shared_user.id,
        organization_id=org_b.id,
        role=UserRole.ADMIN,
    )
    db_session.add(membership)
    await db_session.commit()
    await db_session.refresh(membership)
    return membership


@pytest.fixture
async def employer_in_a(
    db_session: AsyncSession,
    org_a: Organization
) -> Employer:
    """Create employer in Org A."""
    employer = Employer(
        organization_id=org_a.id,
        name="Employer A",
        rfc="RFC-A-123456",
        address="Address A",
    )
    db_session.add(employer)
    await db_session.commit()
    await db_session.refresh(employer)
    return employer


@pytest.fixture
async def employer_in_b(
    db_session: AsyncSession,
    org_b: Organization
) -> Employer:
    """Create employer in Org B."""
    employer = Employer(
        organization_id=org_b.id,
        name="Employer B",
        rfc="RFC-B-789012",
        address="Address B",
    )
    db_session.add(employer)
    await db_session.commit()
    await db_session.refresh(employer)
    return employer


@pytest.fixture
def token_org_a(shared_user: User, org_a: Organization) -> str:
    """Create JWT token for Org A."""
    return create_access_token(
        user_id=shared_user.id,
        org_id=org_a.id,
        role=UserRole.OWNER.value,
    )


@pytest.fixture
def token_org_b(shared_user: User, org_b: Organization) -> str:
    """Create JWT token for Org B."""
    return create_access_token(
        user_id=shared_user.id,
        org_id=org_b.id,
        role=UserRole.ADMIN.value,
    )


# =============================================================================
# Test: Multi-Org Tenant Isolation
# =============================================================================


class TestMultiOrgTenantIsolation:
    """Tests for correct tenant isolation with multiple organizations."""

    @pytest.mark.asyncio
    async def test_user_belongs_to_both_orgs(
        self,
        shared_user: User,
        membership_a: Membership,
        membership_b: Membership,
    ):
        """Test that user has membership in both organizations."""
        assert membership_a.organization_id != membership_b.organization_id
        # Both memberships should exist
        assert membership_a.user_id == shared_user.id
        assert membership_b.user_id == shared_user.id

    @pytest.mark.asyncio
    async def test_get_current_active_organization_uses_token_org_id(
        self,
        db_session: AsyncSession,
        shared_user: User,
        org_a: Organization,
        org_b: Organization,
        membership_a: Membership,
        membership_b: Membership,
        token_org_a: str,
        token_org_b: str,
    ):
        """
        Test that get_current_active_organization uses org_id from JWT.
        
        DT-001 Fix: Previously used first membership by created_at.
        Now correctly uses org_id from JWT token.
        """
        from app.api.deps import get_current_active_organization
        from unittest.mock import MagicMock
        
        # Test with token for Org A
        user_a, org_a_result = await get_current_active_organization(
            request=MagicMock(),
            db=db_session,
            credentials=MagicMock(credentials=token_org_a),
        )
        assert org_a_result.id == org_a.id
        assert org_a_result.name == "Org A"
        
        # Test with token for Org B
        user_b, org_b_result = await get_current_active_organization(
            request=MagicMock(),
            db=db_session,
            credentials=MagicMock(credentials=token_org_b),
        )
        assert org_b_result.id == org_b.id
        assert org_b_result.name == "Org B"

    @pytest.mark.asyncio
    async def test_same_user_different_org_context(
        self,
        db_session: AsyncSession,
        shared_user: User,
        org_a: Organization,
        org_b: Organization,
        membership_a: Membership,
        membership_b: Membership,
    ):
        """Test that same user gets different org context based on token."""
        from app.api.deps import get_current_active_organization
        from unittest.mock import MagicMock
        
        # Create tokens for each org
        token_a = create_access_token(
            user_id=shared_user.id,
            org_id=org_a.id,
            role=UserRole.OWNER.value,
        )
        token_b = create_access_token(
            user_id=shared_user.id,
            org_id=org_b.id,
            role=UserRole.ADMIN.value,
        )
        
        # Get org context with token A
        _, org_context_a = await get_current_active_organization(
            request=MagicMock(),
            db=db_session,
            credentials=MagicMock(credentials=token_a),
        )
        
        # Get org context with token B
        _, org_context_b = await get_current_active_organization(
            request=MagicMock(),
            db=db_session,
            credentials=MagicMock(credentials=token_b),
        )
        
        # Verify different org contexts
        assert org_context_a.id != org_context_b.id
        assert org_context_a.id == org_a.id
        assert org_context_b.id == org_b.id

    @pytest.mark.asyncio
    async def test_employer_isolation_by_org(
        self,
        db_session: AsyncSession,
        employer_in_a: Employer,
        employer_in_b: Employer,
        org_a: Organization,
        org_b: Organization,
    ):
        """Test that employers are correctly isolated by organization."""
        from sqlalchemy import select
        
        # Query employers for Org A only
        result_a = await db_session.execute(
            select(Employer).where(Employer.organization_id == org_a.id)
        )
        employers_a = result_a.scalars().all()
        
        # Query employers for Org B only
        result_b = await db_session.execute(
            select(Employer).where(Employer.organization_id == org_b.id)
        )
        employers_b = result_b.scalars().all()
        
        # Verify isolation
        assert len(employers_a) == 1
        assert employers_a[0].id == employer_in_a.id
        assert employers_a[0].organization_id == org_a.id
        
        assert len(employers_b) == 1
        assert employers_b[0].id == employer_in_b.id
        assert employers_b[0].organization_id == org_b.id
        
        # Cross-tenant query should return nothing
        cross_tenant = await db_session.execute(
            select(Employer).where(
                Employer.organization_id == org_a.id,
                Employer.id == employer_in_b.id,
            )
        )
        assert cross_tenant.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_token_without_org_id_raises_403(
        self,
        db_session: AsyncSession,
        shared_user: User,
    ):
        """Test that token without org_id returns 403."""
        from app.api.deps import get_current_active_organization
        from fastapi import HTTPException
        from unittest.mock import MagicMock
        
        # Create token without org_id
        token_no_org = create_access_token(
            user_id=shared_user.id,
            # No org_id provided
        )
        
        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_organization(
                request=MagicMock(),
                db=db_session,
                credentials=MagicMock(credentials=token_no_org),
            )
        
        assert exc_info.value.status_code == 403
        assert "No organization context" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_token_with_invalid_org_id_raises_403(
        self,
        db_session: AsyncSession,
        shared_user: User,
        membership_a: Membership,
    ):
        """Test that token with org_id user doesn't belong to returns 403."""
        from app.api.deps import get_current_active_organization
        from fastapi import HTTPException
        from unittest.mock import MagicMock
        
        # Create token with org_id user doesn't belong to
        token_invalid_org = create_access_token(
            user_id=shared_user.id,
            org_id=99999,  # Non-existent org
            role=UserRole.OWNER.value,
        )
        
        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_organization(
                request=MagicMock(),
                db=db_session,
                credentials=MagicMock(credentials=token_invalid_org),
            )
        
        assert exc_info.value.status_code == 403
        assert "Not a member" in str(exc_info.value.detail)


class TestMultiOrgCRUDIsolation:
    """Tests for CRUD operations with multi-org isolation."""

    @pytest.mark.asyncio
    async def test_create_employer_uses_token_org_id(
        self,
        db_session: AsyncSession,
        shared_user: User,
        org_a: Organization,
        membership_a: Membership,
        token_org_a: str,
    ):
        """Test that creating employer uses org_id from token."""
        from app.api.employers import create_employer
        from app.schemas.domain import EmployerCreate, EntityStatusEnum
        from unittest.mock import MagicMock
        
        data = EmployerCreate(
            name="New Employer",
            rfc="ABCD123456789",  # 13 chars: 4 letters + 6 digits + 3 alfanum (audit fix)
            address="New Address",
            status=EntityStatusEnum.ACTIVE,
        )
        
        result = await create_employer(
            data=data,
            user_org=(shared_user, org_a),
            db=db_session,
        )
        
        # Verify employer was created in correct org
        assert result.organization_id == org_a.id
        assert result.rfc == "ABCD123456789"  # 13 chars valid RFC (audit fix)

    @pytest.mark.asyncio
    async def test_list_employers_only_returns_org_employers(
        self,
        db_session: AsyncSession,
        shared_user: User,
        org_a: Organization,
        org_b: Organization,
        employer_in_a: Employer,
        employer_in_b: Employer,
        membership_a: Membership,
        membership_b: Membership,
    ):
        """Test that listing employers only returns those from token's org."""
        from sqlalchemy import select
        
        # Query with Org A context
        result_a = await db_session.execute(
            select(Employer).where(Employer.organization_id == org_a.id)
        )
        employers_a = result_a.scalars().all()
        
        # Query with Org B context
        result_b = await db_session.execute(
            select(Employer).where(Employer.organization_id == org_b.id)
        )
        employers_b = result_b.scalars().all()
        
        # Verify isolation
        assert len(employers_a) == 1
        assert employers_a[0].name == "Employer A"
        
        assert len(employers_b) == 1
        assert employers_b[0].name == "Employer B"


# =============================================================================
# Run Tests
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
