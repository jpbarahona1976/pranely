"""
Waste Movement API endpoints - CRUD operations with multi-tenant isolation.

FASE 5B: Waste Domain Implementation
Endpoints: list, create, read, update, archive, stats
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_organization, get_user_role_from_token
from app.core.database import get_db
from app.models import User, Organization, WasteMovement, MovementStatus
from app.schemas.domain import (
    MovementStatusEnum,
    WasteMovementCreate,
    WasteMovementResponse,
    WasteMovementUpdate,
)
from app.core.audit import record_audit_event, AuditAction, AuditSeverity, CorrelationContext


router = APIRouter(prefix="/waste", tags=["Waste Movements"])


# =============================================================================
# Constants
# =============================================================================

# Roles that can mutate waste movements
MUTABLE_ROLES = {"owner", "admin", "member"}


# =============================================================================
# Helper functions
# =============================================================================

def can_mutate(role: str) -> bool:
    """Check if role can mutate (create/update/archive) waste movements."""
    return role in MUTABLE_ROLES


async def get_movement_or_404(
    movement_id: int,
    org_id: int,
    db: AsyncSession,
    include_archived: bool = False,
) -> WasteMovement:
    """
    Get waste movement by ID with tenant isolation.
    
    Args:
        movement_id: Movement ID to fetch
        org_id: Organization ID for tenant isolation
        db: Database session
        include_archived: Whether to include archived movements
    
    Returns:
        WasteMovement instance
    
    Raises:
        HTTPException 404 if not found
    """
    conditions = [
        WasteMovement.id == movement_id,
        WasteMovement.organization_id == org_id,
    ]
    if not include_archived:
        conditions.append(WasteMovement.archived_at.is_(None))
    
    result = await db.execute(
        select(WasteMovement).where(and_(*conditions))
    )
    movement = result.scalar_one_or_none()
    
    if movement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://api.pranely.com/errors/waste-movement",
                "title": "Waste movement not found",
                "status": 404,
                "detail": f"Waste movement with id {movement_id} not found",
            },
        )
    
    return movement


def validate_immutable_update(movement: WasteMovement, update_data: WasteMovementUpdate) -> None:
    """
    Validate that an immutable movement is not being improperly updated.
    
    Args:
        movement: Current movement instance
        update_data: Proposed update data
    
    Raises:
        HTTPException 409 if immutable movement would be modified
    """
    # Check if movement is immutable
    if movement.is_immutable:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://api.pranely.com/errors/waste-movement",
                "title": "Movement is immutable",
                "status": 409,
                "detail": "This waste movement has been validated and cannot be modified. "
                         "To make changes, a new movement must be created.",
            },
        )
    
    # If trying to set is_immutable to True, check if already validated
    if update_data.is_immutable is True and not movement.is_immutable:
        # This is allowed (locking the movement)
        pass


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "",
    response_model=WasteMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create waste movement",
    description="Create a new waste movement/manifest for the current organization.",
)
async def create_waste_movement(
    data: WasteMovementCreate,
    user_org: tuple[User, Organization] = Depends(get_current_active_organization),
    role: str = Depends(get_user_role_from_token),
    db: AsyncSession = Depends(get_db),
) -> WasteMovementResponse:
    """
    Create a new waste movement.
    
    - **manifest_number**: Required manifest document number
    - **movement_type**: Type of movement (optional)
    - **quantity**: Quantity (optional)
    - **unit**: Unit of measure (optional)
    - **date**: Movement date (optional)
    - **status**: Movement status (defaults to pending)
    - **confidence_score**: AI confidence score (optional, set by IA pipeline later)
    - **file_path**: Document file path (optional, set by upload pipeline later)
    - **orig_filename**: Original filename (optional)
    
    Owner, admin, and member roles can create movements.
    Viewer role cannot create movements (returns 403).
    """
    user, org = user_org
    
    if not can_mutate(role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/authz",
                "title": "Permission denied",
                "status": 403,
                "detail": "Viewer role cannot create waste movements",
            },
        )
    
    # Create movement
    movement = WasteMovement(
        organization_id=org.id,
        manifest_number=data.manifest_number,
        movement_type=data.movement_type,
        quantity=data.quantity,
        unit=data.unit,
        date=data.date,
        confidence_score=data.confidence_score,
        status=MovementStatus(data.status.value),
        is_immutable=data.is_immutable,
        file_path=data.file_path,
        orig_filename=data.orig_filename,
    )
    
    db.add(movement)
    await db.commit()
    await db.refresh(movement)
    
    # Audit trail explícito - FIX 5B-FIX-1
    await record_audit_event(
        user_id=user.id,
        organization_id=org.id,
        action=AuditAction.CREATE,
        resource_type="waste_movement",
        resource_id=str(movement.id),
        severity=AuditSeverity.AUDIT,
        metadata={
            "manifest_number": movement.manifest_number,
            "status": movement.status.value,
            "quantity": movement.quantity,
            "unit": movement.unit,
        },
    )
    
    return WasteMovementResponse.model_validate(movement)


@router.get(
    "",
    response_model=dict,
    summary="List waste movements",
    description="List all waste movements for the current organization with pagination.",
)
async def list_waste_movements(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by manifest number"),
    include_archived: bool = Query(False, description="Include archived movements"),
    user_org: tuple[User, Organization] = Depends(get_current_active_organization),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    List waste movements with pagination and filters.
    
    - **page**: Page number (1-based)
    - **page_size**: Items per page (max 100)
    - **status_filter**: Filter by movement status
    - **search**: Search by manifest number
    - **include_archived**: Include archived movements (default: False)
    
    Returns paginated list of movements for the current organization.
    Archived movements are excluded by default.
    """
    user, org = user_org
    
    # Base conditions
    conditions = [WasteMovement.organization_id == org.id]
    
    # Filter by archived status
    if not include_archived:
        conditions.append(WasteMovement.archived_at.is_(None))
    
    # Filter by status
    if status_filter:
        try:
            status_enum = MovementStatus(status_filter)
            conditions.append(WasteMovement.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "https://api.pranely.com/errors/validation",
                    "title": "Invalid status",
                    "status": 400,
                    "detail": f"Invalid status: {status_filter}. Valid values: pending, in_review, validated, rejected, exception",
                },
            )
    
    # Search by manifest number
    if search:
        search_term = f"%{search}%"
        conditions.append(WasteMovement.manifest_number.ilike(search_term))
    
    # Count total
    count_query = select(func.count()).select_from(WasteMovement).where(and_(*conditions))
    total = (await db.execute(count_query)).scalar() or 0
    
    # Get paginated results
    offset = (page - 1) * page_size
    query = (
        select(WasteMovement)
        .where(and_(*conditions))
        .order_by(WasteMovement.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = result.scalars().all()
    
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return {
        "items": [WasteMovementResponse.model_validate(r) for r in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get(
    "/stats",
    response_model=dict,
    summary="Get waste movement statistics",
    description="Get aggregated statistics for waste movements in the current organization.",
)
async def get_waste_stats(
    user_org: tuple[User, Organization] = Depends(get_current_active_organization),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get waste movement statistics for dashboard.
    
    Returns aggregated counts by status:
    - **total**: Total active movements (not archived)
    - **by_status**: Count of movements per status
    - **archived_count**: Total archived movements
    
    Only returns data for the current organization (tenant isolation).
    """
    user, org = user_org
    
    # Count active movements by status
    status_counts = {}
    for status_val in MovementStatus:
        count_query = select(func.count()).select_from(WasteMovement).where(
            and_(
                WasteMovement.organization_id == org.id,
                WasteMovement.status == status_val,
                WasteMovement.archived_at.is_(None),
            )
        )
        count = (await db.execute(count_query)).scalar() or 0
        status_counts[status_val.value] = count
    
    # Count total active
    total_active_query = select(func.count()).select_from(WasteMovement).where(
        and_(
            WasteMovement.organization_id == org.id,
            WasteMovement.archived_at.is_(None),
        )
    )
    total_active = (await db.execute(total_active_query)).scalar() or 0
    
    # Count archived
    archived_query = select(func.count()).select_from(WasteMovement).where(
        and_(
            WasteMovement.organization_id == org.id,
            WasteMovement.archived_at.is_not(None),
        )
    )
    archived_count = (await db.execute(archived_query)).scalar() or 0
    
    return {
        "total": total_active,
        "by_status": status_counts,
        "archived_count": archived_count,
    }


@router.get(
    "/{movement_id}",
    response_model=WasteMovementResponse,
    summary="Get waste movement",
    description="Get a specific waste movement by ID.",
)
async def get_waste_movement(
    movement_id: int,
    user_org: tuple[User, Organization] = Depends(get_current_active_organization),
    db: AsyncSession = Depends(get_db),
) -> WasteMovementResponse:
    """
    Get waste movement by ID.
    
    - **movement_id**: ID of the movement to retrieve
    
    Returns 404 if movement not found or belongs to different organization.
    """
    user, org = user_org
    
    movement = await get_movement_or_404(movement_id, org.id, db)
    
    return WasteMovementResponse.model_validate(movement)


@router.patch(
    "/{movement_id}",
    response_model=WasteMovementResponse,
    summary="Update waste movement",
    description="Update an existing waste movement. Immutable movements cannot be modified.",
)
async def update_waste_movement(
    movement_id: int,
    data: WasteMovementUpdate,
    user_org: tuple[User, Organization] = Depends(get_current_active_organization),
    role: str = Depends(get_user_role_from_token),
    db: AsyncSession = Depends(get_db),
) -> WasteMovementResponse:
    """
    Update a waste movement.
    
    - **manifest_number**: New manifest number (optional)
    - **movement_type**: New movement type (optional)
    - **quantity**: New quantity (optional)
    - **unit**: New unit (optional)
    - **date**: New date (optional)
    - **status**: New status (optional)
    - **is_immutable**: Set to True to lock movement (optional)
    - **archived_at**: Archive timestamp (optional)
    
    Returns 409 Conflict if movement is immutable.
    Returns 403 Forbidden for viewer role.
    Returns 404 if movement not found.
    """
    user, org = user_org
    
    # Check RBAC
    if not can_mutate(role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/authz",
                "title": "Permission denied",
                "status": 403,
                "detail": "Viewer role cannot update waste movements",
            },
        )
    
    # Get existing movement
    movement = await get_movement_or_404(movement_id, org.id, db)
    
    # Check immutable status BEFORE updating
    if data.is_immutable is not None:
        # User is trying to modify immutable flag
        if movement.is_immutable:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "type": "https://api.pranely.com/errors/waste-movement",
                    "title": "Movement is immutable",
                    "status": 409,
                    "detail": "This waste movement has been validated and cannot be modified.",
                },
            )
    else:
        # Normal update - check if already immutable
        if movement.is_immutable:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "type": "https://api.pranely.com/errors/waste-movement",
                    "title": "Movement is immutable",
                    "status": 409,
                    "detail": "This waste movement has been validated and cannot be modified.",
                },
            )
    
    # Update fields if provided
    update_data = data.model_dump(exclude_unset=True)
    changed_fields = {}
    
    for field, value in update_data.items():
        if field == "status" and value is not None:
            old_value = movement.status.value if movement.status else None
            value = MovementStatus(value.value) if hasattr(value, 'value') else MovementStatus(value)
            changed_fields["status"] = {"from": old_value, "to": value.value}
        
        if value is not None:
            old_value = getattr(movement, field, None)
            if old_value != value:
                changed_fields[field] = {"from": str(old_value), "to": str(value)}
            setattr(movement, field, value)
    
    # Update timestamp
    movement.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(movement)
    
    # Audit trail explícito - FIX 5B-FIX-1
    await record_audit_event(
        user_id=user.id,
        organization_id=org.id,
        action=AuditAction.UPDATE,
        resource_type="waste_movement",
        resource_id=str(movement.id),
        severity=AuditSeverity.AUDIT,
        metadata={
            "manifest_number": movement.manifest_number,
            "changed_fields": changed_fields,
            "new_status": movement.status.value,
        },
    )
    
    return WasteMovementResponse.model_validate(movement)


@router.post(
    "/{movement_id}/archive",
    response_model=WasteMovementResponse,
    summary="Archive waste movement",
    description="Archive (soft-delete) a waste movement.",
)
async def archive_waste_movement(
    movement_id: int,
    user_org: tuple[User, Organization] = Depends(get_current_active_organization),
    role: str = Depends(get_user_role_from_token),
    db: AsyncSession = Depends(get_db),
) -> WasteMovementResponse:
    """
    Archive (soft-delete) a waste movement.
    
    - Sets archived_at to current timestamp
    - Movement no longer appears in default listings
    - Can still be retrieved with include_archived=true
    
    Returns 404 if movement not found.
    Returns 400 if already archived.
    Returns 403 Forbidden for viewer role.
    """
    user, org = user_org
    
    # Check RBAC
    if not can_mutate(role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/authz",
                "title": "Permission denied",
                "status": 403,
                "detail": "Viewer role cannot archive waste movements",
            },
        )
    
    # Get movement (allow archiving already archived to return proper error)
    movement = await get_movement_or_404(
        movement_id, org.id, db, include_archived=True
    )
    
    # Check if already archived
    if movement.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/waste-movement",
                "title": "Already archived",
                "status": 400,
                "detail": "This waste movement is already archived",
            },
        )
    
    # Archive the movement
    movement.archived_at = datetime.now(timezone.utc)
    movement.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(movement)
    
    # Audit trail explícito - FIX 5B-FIX-1
    await record_audit_event(
        user_id=user.id,
        organization_id=org.id,
        action=AuditAction.ARCHIVE,  # Archive es soft-delete, usar acción semánticamente correcta
        resource_type="waste_movement",
        resource_id=str(movement.id),
        severity=AuditSeverity.AUDIT,
        metadata={
            "manifest_number": movement.manifest_number,
            "status_before_archive": movement.status.value,
            "archived_at": movement.archived_at.isoformat() if movement.archived_at else None,
            "action": "soft_delete",
        },
    )
    
    return WasteMovementResponse.model_validate(movement)
