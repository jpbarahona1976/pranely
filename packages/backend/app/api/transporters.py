"""Transporter API endpoints - CRUD operations with multi-tenant isolation."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.org_deps import get_current_org
from app.core.database import get_db
from app.models import EntityStatus, Organization, Transporter
from app.schemas.domain import (
    TransporterCreate,
    TransporterListResponse,
    TransporterResponse,
    TransporterUpdate,
)

router = APIRouter(prefix="/transporters", tags=["Transporters"])


@router.post(
    "",
    response_model=TransporterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create transporter",
    description="Create a new transporter for the current organization.",
)
async def create_transporter(
    data: TransporterCreate,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> TransporterResponse:
    """Create a new transporter."""
    # Check RFC uniqueness within tenant
    existing = await db.execute(
        select(Transporter).where(
            and_(
                Transporter.organization_id == org.id,
                Transporter.rfc == data.rfc,
                Transporter.archived_at.is_(None),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/transporter",
                "title": "Duplicate RFC",
                "status": 400,
                "detail": f"RFC {data.rfc} already exists in this organization",
            },
        )
    
    transporter = Transporter(
        organization_id=org.id,
        name=data.name,
        rfc=data.rfc.upper(),
        address=data.address,
        contact_phone=data.contact_phone,
        email=data.email,
        license_number=data.license_number,
        vehicle_plate=data.vehicle_plate,
        status=EntityStatus(data.status.value),
        archived_at=data.archived_at,
        extra_data=data.extra_data,
    )
    db.add(transporter)
    await db.commit()
    await db.refresh(transporter)
    
    return TransporterResponse.model_validate(transporter)


@router.get(
    "",
    response_model=TransporterListResponse,
    summary="List transporters",
    description="List all transporters for the current organization with pagination.",
)
async def list_transporters(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by name or RFC"),
    include_archived: bool = Query(False, description="Include archived transporters"),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> TransporterListResponse:
    """List transporters with pagination and filters."""
    # Base conditions
    conditions = [Transporter.organization_id == org.id]
    if not include_archived:
        conditions.append(Transporter.archived_at.is_(None))
    if status_filter:
        conditions.append(Transporter.status == EntityStatus(status_filter))
    if search:
        search_term = f"%{search}%"
        conditions.append(
            or_(
                Transporter.name.ilike(search_term),
                Transporter.rfc.ilike(search_term),
            )
        )
    
    # Count total
    count_query = select(func.count()).select_from(Transporter).where(and_(*conditions))
    total = (await db.execute(count_query)).scalar() or 0
    
    # Get paginated results
    offset = (page - 1) * page_size
    query = (
        select(Transporter)
        .where(and_(*conditions))
        .order_by(Transporter.name)
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = result.scalars().all()
    
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return TransporterListResponse(
        items=[TransporterResponse.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{transporter_id}",
    response_model=TransporterResponse,
    summary="Get transporter",
    description="Get a specific transporter by ID.",
)
async def get_transporter(
    transporter_id: int,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> TransporterResponse:
    """Get transporter by ID."""
    result = await db.execute(
        select(Transporter).where(
            and_(
                Transporter.id == transporter_id,
                Transporter.organization_id == org.id,
                Transporter.archived_at.is_(None),
            )
        )
    )
    transporter = result.scalar_one_or_none()
    
    if transporter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/transporter",
                "title": "Transporter not found",
                "status": 404,
                "detail": f"Transporter with id {transporter_id} not found",
            },
        )
    
    return TransporterResponse.model_validate(transporter)


@router.patch(
    "/{transporter_id}",
    response_model=TransporterResponse,
    summary="Update transporter",
    description="Update an existing transporter.",
)
async def update_transporter(
    transporter_id: int,
    data: TransporterUpdate,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> TransporterResponse:
    """Update a transporter."""
    result = await db.execute(
        select(Transporter).where(
            and_(
                Transporter.id == transporter_id,
                Transporter.organization_id == org.id,
                Transporter.archived_at.is_(None),
            )
        )
    )
    transporter = result.scalar_one_or_none()
    
    if transporter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/transporter",
                "title": "Transporter not found",
                "status": 404,
                "detail": f"Transporter with id {transporter_id} not found",
            },
        )
    
    # Update fields if provided
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "rfc" and value is not None:
            value = value.upper()
            # Check RFC uniqueness (exclude current transporter)
            existing = await db.execute(
                select(Transporter).where(
                    and_(
                        Transporter.organization_id == org.id,
                        Transporter.rfc == value,
                        Transporter.id != transporter_id,
                        Transporter.archived_at.is_(None),
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "type": "https://api.pranely.com/errors/transporter",
                        "title": "Duplicate RFC",
                        "status": 400,
                        "detail": f"RFC {value} already exists in this organization",
                    },
                )
        if field == "status" and value is not None:
            value = EntityStatus(value.value)
        
        if value is not None:
            setattr(transporter, field, value)
    
    await db.commit()
    await db.refresh(transporter)
    
    return TransporterResponse.model_validate(transporter)


@router.delete(
    "/{transporter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Archive transporter",
    description="Soft-delete a transporter by setting archived_at.",
)
async def archive_transporter(
    transporter_id: int,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Archive (soft-delete) a transporter."""
    result = await db.execute(
        select(Transporter).where(
            and_(
                Transporter.id == transporter_id,
                Transporter.organization_id == org.id,
                Transporter.archived_at.is_(None),
            )
        )
    )
    transporter = result.scalar_one_or_none()
    
    if transporter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/transporter",
                "title": "Transporter not found",
                "status": 404,
                "detail": f"Transporter with id {transporter_id} not found",
            },
        )
    
    # Soft delete
    transporter.archived_at = datetime.now(timezone.utc)
    await db.commit()