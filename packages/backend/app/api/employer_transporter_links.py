"""EmployerTransporterLink API endpoints - CRUD operations with multi-tenant isolation."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_organization
from app.core.database import get_db
from app.models import Employer, EmployerTransporterLink, User, Organization, Transporter
from app.schemas.domain import (
    EmployerTransporterLinkCreate,
    EmployerTransporterLinkResponse,
    EmployerTransporterLinkUpdate,
)

router = APIRouter(prefix="/employer-transporter-links", tags=["Employer Transporter Links"])


@router.post(
    "",
    response_model=EmployerTransporterLinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create link",
    description="Create a new link between an employer and a transporter.",
)
async def create_link(
    data: EmployerTransporterLinkCreate,
    user_org: tuple[User, Organization] = Depends(get_current_active_organization),
    db: AsyncSession = Depends(get_db),
) -> EmployerTransporterLinkResponse:
    """Create a new employer-transporter link."""
    user, org = user_org
    
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
                "type": "https://api.pranely.com/errors/link",
                "title": "Employer not found",
                "status": 404,
                "detail": f"Employer with id {data.employer_id} not found or belongs to different organization",
            },
        )
    
    # Verify transporter belongs to current tenant
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
                "type": "https://api.pranely.com/errors/link",
                "title": "Transporter not found",
                "status": 404,
                "detail": f"Transporter with id {data.transporter_id} not found or belongs to different organization",
            },
        )
    
    # Check for existing link (unique constraint)
    existing = await db.execute(
        select(EmployerTransporterLink).where(
            and_(
                EmployerTransporterLink.organization_id == org.id,
                EmployerTransporterLink.employer_id == data.employer_id,
                EmployerTransporterLink.transporter_id == data.transporter_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/link",
                "title": "Link already exists",
                "status": 400,
                "detail": "Link between this employer and transporter already exists",
            },
        )
    
    link = EmployerTransporterLink(
        organization_id=org.id,
        employer_id=data.employer_id,
        transporter_id=data.transporter_id,
        is_authorized=data.is_authorized,
        notes=data.notes,
        authorization_date=datetime.now(timezone.utc) if data.is_authorized else None,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    
    return EmployerTransporterLinkResponse.model_validate(link)


@router.get(
    "",
    response_model=list[EmployerTransporterLinkResponse],
    summary="List links",
    description="List all employer-transporter links for the current organization.",
)
async def list_links(
    employer_id: Optional[int] = Query(None, description="Filter by employer"),
    transporter_id: Optional[int] = Query(None, description="Filter by transporter"),
    is_authorized: Optional[bool] = Query(None, description="Filter by authorization status"),
    user_org: tuple[User, Organization] = Depends(get_current_active_organization),
    db: AsyncSession = Depends(get_db),
) -> list[EmployerTransporterLinkResponse]:
    """List employer-transporter links."""
    user, org = user_org
    
    conditions = [EmployerTransporterLink.organization_id == org.id]
    
    if employer_id is not None:
        conditions.append(EmployerTransporterLink.employer_id == employer_id)
    if transporter_id is not None:
        conditions.append(EmployerTransporterLink.transporter_id == transporter_id)
    if is_authorized is not None:
        conditions.append(EmployerTransporterLink.is_authorized == is_authorized)
    
    query = (
        select(EmployerTransporterLink)
        .where(and_(*conditions))
        .order_by(EmployerTransporterLink.created_at.desc())
    )
    result = await db.execute(query)
    items = result.scalars().all()
    
    return [EmployerTransporterLinkResponse.model_validate(link) for link in items]


@router.get(
    "/{link_id}",
    response_model=EmployerTransporterLinkResponse,
    summary="Get link",
    description="Get a specific link by ID.",
)
async def get_link(
    link_id: int,
    user_org: tuple[User, Organization] = Depends(get_current_active_organization),
    db: AsyncSession = Depends(get_db),
) -> EmployerTransporterLinkResponse:
    """Get link by ID."""
    user, org = user_org
    
    result = await db.execute(
        select(EmployerTransporterLink).where(
            and_(
                EmployerTransporterLink.id == link_id,
                EmployerTransporterLink.organization_id == org.id,
            )
        )
    )
    link = result.scalar_one_or_none()
    
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/link",
                "title": "Link not found",
                "status": 404,
                "detail": f"Link with id {link_id} not found",
            },
        )
    
    return EmployerTransporterLinkResponse.model_validate(link)


@router.patch(
    "/{link_id}",
    response_model=EmployerTransporterLinkResponse,
    summary="Update link",
    description="Update an existing link.",
)
async def update_link(
    link_id: int,
    data: EmployerTransporterLinkUpdate,
    user_org: tuple[User, Organization] = Depends(get_current_active_organization),
    db: AsyncSession = Depends(get_db),
) -> EmployerTransporterLinkResponse:
    """Update a link."""
    user, org = user_org
    
    result = await db.execute(
        select(EmployerTransporterLink).where(
            and_(
                EmployerTransporterLink.id == link_id,
                EmployerTransporterLink.organization_id == org.id,
            )
        )
    )
    link = result.scalar_one_or_none()
    
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/link",
                "title": "Link not found",
                "status": 404,
                "detail": f"Link with id {link_id} not found",
            },
        )
    
    # Update fields if provided
    if data.is_authorized is not None:
        link.is_authorized = data.is_authorized
        if data.is_authorized and link.authorization_date is None:
            link.authorization_date = datetime.now(timezone.utc)
    
    if data.notes is not None:
        link.notes = data.notes
    
    await db.commit()
    await db.refresh(link)
    
    return EmployerTransporterLinkResponse.model_validate(link)


@router.delete(
    "/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete link",
    description="Delete an employer-transporter link.",
)
async def delete_link(
    link_id: int,
    user_org: tuple[User, Organization] = Depends(get_current_active_organization),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a link."""
    user, org = user_org
    
    result = await db.execute(
        select(EmployerTransporterLink).where(
            and_(
                EmployerTransporterLink.id == link_id,
                EmployerTransporterLink.organization_id == org.id,
            )
        )
    )
    link = result.scalar_one_or_none()
    
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/link",
                "title": "Link not found",
                "status": 404,
                "detail": f"Link with id {link_id} not found",
            },
        )
    
    await db.delete(link)
    await db.commit()
