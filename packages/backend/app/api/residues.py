"""Residue API endpoints - CRUD operations with multi-tenant isolation."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.org_deps import get_current_org
from app.core.database import get_db
from app.models import Employer, EntityStatus, Organization, Residue, Transporter, WasteStatus, WasteType
from app.schemas.domain import (
    ResidueCreate,
    ResidueListResponse,
    ResidueResponse,
    ResidueUpdate,
)

router = APIRouter(prefix="/residues", tags=["Residues"])


@router.post(
    "",
    response_model=ResidueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create residue",
    description="Create a new residue for the current organization.",
)
async def create_residue(
    data: ResidueCreate,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> ResidueResponse:
    """Create a new residue."""
    # Verify employer belongs to current tenant
    employer_result = await db.execute(
        select(Employer).where(
            and_(
                Employer.id == data.employer_id,
                Employer.organization_id == org.id,
                Employer.archived_at.is_(None),
            )
        )
    )
    employer = employer_result.scalar_one_or_none()
    if employer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/residue",
                "title": "Employer not found",
                "status": 404,
                "detail": f"Employer with id {data.employer_id} not found or belongs to different organization",
            },
        )
    
    # Verify transporter if provided (belongs to current tenant)
    if data.transporter_id is not None:
        transporter_result = await db.execute(
            select(Transporter).where(
                and_(
                    Transporter.id == data.transporter_id,
                    Transporter.organization_id == org.id,
                    Transporter.archived_at.is_(None),
                )
            )
        )
        transporter = transporter_result.scalar_one_or_none()
        if transporter is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "type": "https://api.pranely.com/errors/residue",
                    "title": "Transporter not found",
                    "status": 404,
                    "detail": f"Transporter with id {data.transporter_id} not found or belongs to different organization",
                },
            )
    
    residue = Residue(
        organization_id=org.id,
        employer_id=data.employer_id,
        transporter_id=data.transporter_id,
        name=data.name,
        waste_type=WasteType(data.waste_type.value),
        un_code=data.un_code,
        hs_code=data.hs_code,
        description=data.description,
        weight_kg=data.weight_kg,
        volume_m3=data.volume_m3,
        status=WasteStatus(data.status.value),
        extra_data=data.extra_data,
    )
    db.add(residue)
    await db.commit()
    await db.refresh(residue)
    
    return ResidueResponse.model_validate(residue)


@router.get(
    "",
    response_model=ResidueListResponse,
    summary="List residues",
    description="List all residues for the current organization with pagination.",
)
async def list_residues(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    waste_type_filter: Optional[str] = Query(None, description="Filter by waste type"),
    employer_id: Optional[int] = Query(None, description="Filter by employer"),
    search: Optional[str] = Query(None, description="Search by name"),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> ResidueListResponse:
    """List residues with pagination and filters."""
    # Base conditions
    conditions = [Residue.organization_id == org.id]
    if status_filter:
        conditions.append(Residue.status == WasteStatus(status_filter))
    if waste_type_filter:
        conditions.append(Residue.waste_type == WasteType(waste_type_filter))
    if employer_id:
        conditions.append(Residue.employer_id == employer_id)
    if search:
        search_term = f"%{search}%"
        conditions.append(Residue.name.ilike(search_term))
    
    # Count total
    count_query = select(func.count()).select_from(Residue).where(and_(*conditions))
    total = (await db.execute(count_query)).scalar() or 0
    
    # Get paginated results
    offset = (page - 1) * page_size
    query = (
        select(Residue)
        .where(and_(*conditions))
        .order_by(Residue.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = result.scalars().all()
    
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return ResidueListResponse(
        items=[ResidueResponse.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{residue_id}",
    response_model=ResidueResponse,
    summary="Get residue",
    description="Get a specific residue by ID.",
)
async def get_residue(
    residue_id: int,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> ResidueResponse:
    """Get residue by ID."""
    result = await db.execute(
        select(Residue).where(
            and_(
                Residue.id == residue_id,
                Residue.organization_id == org.id,
            )
        )
    )
    residue = result.scalar_one_or_none()
    
    if residue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/residue",
                "title": "Residue not found",
                "status": 404,
                "detail": f"Residue with id {residue_id} not found",
            },
        )
    
    return ResidueResponse.model_validate(residue)


@router.patch(
    "/{residue_id}",
    response_model=ResidueResponse,
    summary="Update residue",
    description="Update an existing residue.",
)
async def update_residue(
    residue_id: int,
    data: ResidueUpdate,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> ResidueResponse:
    """Update a residue."""
    result = await db.execute(
        select(Residue).where(
            and_(
                Residue.id == residue_id,
                Residue.organization_id == org.id,
            )
        )
    )
    residue = result.scalar_one_or_none()
    
    if residue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/residue",
                "title": "Residue not found",
                "status": 404,
                "detail": f"Residue with id {residue_id} not found",
            },
        )
    
    # Update fields if provided
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "transporter_id" and value is not None:
            # Verify transporter belongs to current tenant
            transporter_result = await db.execute(
                select(Transporter).where(
                    and_(
                        Transporter.id == value,
                        Transporter.organization_id == org.id,
                        Transporter.archived_at.is_(None),
                    )
                )
            )
            transporter = transporter_result.scalar_one_or_none()
            if transporter is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "type": "https://api.pranely.com/errors/residue",
                        "title": "Transporter not found",
                        "status": 404,
                        "detail": f"Transporter with id {value} not found or belongs to different organization",
                    },
                )
        if field == "status" and value is not None:
            value = WasteStatus(value.value)
        if field == "waste_type" and value is not None:
            value = WasteType(value.value)
        
        if value is not None:
            setattr(residue, field, value)
    
    await db.commit()
    await db.refresh(residue)
    
    return ResidueResponse.model_validate(residue)


@router.delete(
    "/{residue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete residue",
    description="Delete a residue (hard delete for residues, no soft-delete).",
)
async def delete_residue(
    residue_id: int,
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a residue."""
    result = await db.execute(
        select(Residue).where(
            and_(
                Residue.id == residue_id,
                Residue.organization_id == org.id,
            )
        )
    )
    residue = result.scalar_one_or_none()
    
    if residue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/residue",
                "title": "Residue not found",
                "status": 404,
                "detail": f"Residue with id {residue_id} not found",
            },
        )
    
    await db.delete(residue)
    await db.commit()