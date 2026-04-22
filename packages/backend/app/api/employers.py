"""Employer API endpoints - CRUD operations with multi-tenant isolation."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.org_deps import get_current_org
from app.core.database import get_db
from app.models import Employer, EntityStatus, Organization
from app.schemas.domain import (
    EmployerCreate,
    EmployerListResponse,
    EmployerResponse,
    EmployerUpdate,
)

router = APIRouter(prefix="/employers", tags=["Employers"])


def _apply_tenant_filter(query, org_id: int, include_archived: bool = False):
    """Apply tenant isolation filter to query."""
    conditions = [Employer.organization_id == org_id]
    if not include_archived:
        conditions.append(Employer.archived_at.is_(None))
    return query.where(and_(*conditions))


@router.post(
    "",
    response_model=EmployerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create employer",
    description="Create a new employer for the current organization.",
)
async def create_employer(
    data: EmployerCreate,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> EmployerResponse:
    """Create a new employer."""
    # Check RFC uniqueness within tenant
    existing = await db.execute(
        select(Employer).where(
            and_(
                Employer.organization_id == org.id,
                Employer.rfc == data.rfc,
                Employer.archived_at.is_(None),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/employer",
                "title": "Duplicate RFC",
                "status": 400,
                "detail": f"RFC {data.rfc} already exists in this organization",
            },
        )
    
    employer = Employer(
        organization_id=org.id,
        name=data.name,
        rfc=data.rfc.upper(),
        address=data.address,
        contact_phone=data.contact_phone,
        email=data.email,
        website=data.website,
        industry=data.industry,
        status=EntityStatus(data.status.value),
        archived_at=data.archived_at,
        extra_data=data.extra_data,
    )
    db.add(employer)
    await db.commit()
    await db.refresh(employer)
    
    return EmployerResponse.model_validate(employer)


@router.get(
    "",
    response_model=EmployerListResponse,
    summary="List employers",
    description="List all employers for the current organization with pagination.",
)
async def list_employers(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name or RFC"),
    include_archived: bool = Query(False, description="Include archived employers"),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> EmployerListResponse:
    """List employers with pagination and filters."""
    # Base conditions
    conditions = [Employer.organization_id == org.id]
    if not include_archived:
        conditions.append(Employer.archived_at.is_(None))
    if status_filter:
        conditions.append(Employer.status == EntityStatus(status_filter))
    if search:
        search_term = f"%{search}%"
        conditions.append(
            or_(
                Employer.name.ilike(search_term),
                Employer.rfc.ilike(search_term),
            )
        )
    
    # Count total
    count_query = select(func.count()).select_from(Employer).where(and_(*conditions))
    total = (await db.execute(count_query)).scalar() or 0
    
    # Get paginated results
    offset = (page - 1) * page_size
    query = (
        select(Employer)
        .where(and_(*conditions))
        .order_by(Employer.name)
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = result.scalars().all()
    
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return EmployerListResponse(
        items=[EmployerResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{employer_id}",
    response_model=EmployerResponse,
    summary="Get employer",
    description="Get a specific employer by ID.",
)
async def get_employer(
    employer_id: int,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> EmployerResponse:
    """Get employer by ID."""
    result = await db.execute(
        select(Employer).where(
            and_(
                Employer.id == employer_id,
                Employer.organization_id == org.id,
                Employer.archived_at.is_(None),
            )
        )
    )
    employer = result.scalar_one_or_none()
    
    if employer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/employer",
                "title": "Employer not found",
                "status": 404,
                "detail": f"Employer with id {employer_id} not found",
            },
        )
    
    return EmployerResponse.model_validate(employer)


@router.patch(
    "/{employer_id}",
    response_model=EmployerResponse,
    summary="Update employer",
    description="Update an existing employer.",
)
async def update_employer(
    employer_id: int,
    data: EmployerUpdate,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> EmployerResponse:
    """Update an employer."""
    result = await db.execute(
        select(Employer).where(
            and_(
                Employer.id == employer_id,
                Employer.organization_id == org.id,
                Employer.archived_at.is_(None),
            )
        )
    )
    employer = result.scalar_one_or_none()
    
    if employer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/employer",
                "title": "Employer not found",
                "status": 404,
                "detail": f"Employer with id {employer_id} not found",
            },
        )
    
    # Update fields if provided
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "rfc" and value is not None:
            value = value.upper()
            # Check RFC uniqueness (exclude current employer)
            existing = await db.execute(
                select(Employer).where(
                    and_(
                        Employer.organization_id == org.id,
                        Employer.rfc == value,
                        Employer.id != employer_id,
                        Employer.archived_at.is_(None),
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "type": "https://api.pranely.com/errors/employer",
                        "title": "Duplicate RFC",
                        "status": 400,
                        "detail": f"RFC {value} already exists in this organization",
                    },
                )
        if field == "status" and value is not None:
            value = EntityStatus(value.value)
        
        if value is not None:
            setattr(employer, field, value)
    
    await db.commit()
    await db.refresh(employer)
    
    return EmployerResponse.model_validate(employer)


@router.delete(
    "/{employer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Archive employer",
    description="Soft-delete an employer by setting archived_at.",
)
async def archive_employer(
    employer_id: int,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Archive (soft-delete) an employer."""
    result = await db.execute(
        select(Employer).where(
            and_(
                Employer.id == employer_id,
                Employer.organization_id == org.id,
                Employer.archived_at.is_(None),
            )
        )
    )
    employer = result.scalar_one_or_none()
    
    if employer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/employer",
                "title": "Employer not found",
                "status": 404,
                "detail": f"Employer with id {employer_id} not found",
            },
        )
    
    # Soft delete
    employer.archived_at = datetime.now(timezone.utc)
    await db.commit()