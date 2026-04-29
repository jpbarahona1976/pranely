"""
Waste Review API - Endpoints para approve/reject de movements (Fase 6B)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_active_organization
from app.models import User, Organization, Membership, WasteMovement

router = APIRouter(prefix="/waste", tags=["waste-review"])


class ReviewActionRequest(BaseModel):
    """Request para acciones de revisión de waste movement."""
    action: Literal["approve", "reject", "request_changes"]
    reason: Optional[str] = Field(None, description="Razón del rechazo o comentarios")
    comments: Optional[str] = Field(None, description="Comentarios adicionales")


class ReviewActionResponse(BaseModel):
    """Response de acción de revisión."""
    success: bool
    message: str
    movement_id: int
    new_status: str
    reviewed_by: str


def check_can_review(user: User, membership: Membership) -> bool:
    """Verifica si el usuario tiene permisos de revisión."""
    if membership.role.value in ["owner", "admin"]:
        return True
    return False


def check_can_mutate(user: User, membership: Membership, movement: WasteMovement) -> bool:
    """Verifica si el usuario puede mutar el movimiento."""
    # Owner/Admin pueden mutar cualquier movimiento de su org
    if membership.role.value in ["owner", "admin"]:
        return True
    # Member solo puede mutar si lo creó
    if membership.role.value == "member" and movement.created_by_user_id == user.id:
        return True
    return False


@router.post("/{movement_id}/review", response_model=ReviewActionResponse)
async def review_waste_movement(
    movement_id: int,
    review_data: ReviewActionRequest,
    user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_active_organization),
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint para revisar (approve/reject/request_changes) un waste movement.
    
    - **movement_id**: ID del movimiento a revisar
    - **action**: approve | reject | request_changes
    - **reason**: Razón del rechazo (requerido para reject)
    - **comments**: Comentarios adicionales (opcional)
    
    Permisos:
    - Owner/Admin: Pueden aprobar/rechazar cualquier movimiento
    - Viewer: Solo lectura, no puede revisar
    - Member: No puede revisar (solo owner/admin)
    """
    # Obtener el membership del usuario
    membership_result = await db.execute(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == org.id
        )
    )
    membership = membership_result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No eres miembro de esta organización"
        )
    
    # Verificar permisos de revisión
    if not check_can_review(user, membership):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para revisar movimientos"
        )
    
    # Obtener el movimiento
    result = await db.execute(
        select(WasteMovement).where(
            WasteMovement.id == movement_id,
            WasteMovement.organization_id == org.id
        )
    )
    movement = result.scalar_one_or_none()
    
    if not movement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimiento no encontrado"
        )
    
    # Verificar si el movimiento es inmutable (ya validado)
    if movement.is_immutable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede modificar un movimiento validado"
        )
    
    # Ejecutar la acción
    if review_data.action == "approve":
        movement.status = "validated"
        movement.is_immutable = True
        movement.reviewed_by = user.email
        movement.reviewed_at = datetime.utcnow()
        message = "Movimiento aprobado exitosamente"
        new_status = "validated"
        
    elif review_data.action == "reject":
        if not review_data.reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere una razón para rechazar"
            )
        movement.status = "rejected"
        movement.rejection_reason = review_data.reason
        movement.reviewed_by = user.email
        movement.reviewed_at = datetime.utcnow()
        message = f"Movimiento rechazado: {review_data.reason}"
        new_status = "rejected"
        
    elif review_data.action == "request_changes":
        movement.status = "pending"
        movement.rejection_reason = review_data.comments or "Se requieren cambios"
        message = "Se han solicitado cambios"
        new_status = "pending"
        
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Acción no válida: {review_data.action}"
        )
    
    movement.updated_at = datetime.utcnow()
    await db.commit()
    
    return ReviewActionResponse(
        success=True,
        message=message,
        movement_id=movement_id,
        new_status=new_status,
        reviewed_by=user.email
    )


class WasteMovementUpdate(BaseModel):
    """Schema para actualizar waste movement."""
    manifest_number: Optional[str] = None
    date: Optional[str] = None
    waste_type: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    generator_name: Optional[str] = None
    transporter_name: Optional[str] = None
    final_destination: Optional[str] = None


@router.patch("/{movement_id}", response_model=dict)
async def update_waste_movement(
    movement_id: int,
    update_data: WasteMovementUpdate,
    user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_active_organization),
    db: AsyncSession = Depends(get_db),
):
    """
    Actualizar un waste movement.
    
    Solo usuarios con permisos de edición pueden actualizar.
    Movimientos validados (is_immutable=True) no pueden ser modificados.
    """
    # Obtener membership
    membership_result = await db.execute(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == org.id
        )
    )
    membership = membership_result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No eres miembro de esta organización"
        )
    
    # Obtener movimiento
    result = await db.execute(
        select(WasteMovement).where(
            WasteMovement.id == movement_id,
            WasteMovement.organization_id == org.id
        )
    )
    movement = result.scalar_one_or_none()
    
    if not movement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimiento no encontrado"
        )
    
    # Verificar permisos
    if not check_can_mutate(user, membership, movement):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para editar este movimiento"
        )
    
    # Verificar inmutabilidad
    if movement.is_immutable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede modificar un movimiento validado"
        )
    
    # Aplicar actualizaciones
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        if hasattr(movement, field):
            setattr(movement, field, value)
    
    movement.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"success": True, "message": "Movimiento actualizado", "id": movement_id}


@router.post("/{movement_id}/archive", response_model=dict)
async def archive_waste_movement(
    movement_id: int,
    user: User = Depends(get_current_active_user),
    org: Organization = Depends(get_current_active_organization),
    db: AsyncSession = Depends(get_db),
):
    """
    Archivar (soft-delete) un waste movement.
    
    Solo owner/admin pueden archivar.
    Movimientos validados no pueden ser archivados.
    """
    membership_result = await db.execute(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == org.id
        )
    )
    membership = membership_result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No eres miembro de esta organización"
        )
    
    if membership.role.value not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo owner/admin pueden archivar movimientos"
        )
    
    result = await db.execute(
        select(WasteMovement).where(
            WasteMovement.id == movement_id,
            WasteMovement.organization_id == org.id
        )
    )
    movement = result.scalar_one_or_none()
    
    if not movement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimiento no encontrado"
        )
    
    if movement.is_immutable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede archivar un movimiento validado"
        )
    
    movement.status = "archived"
    movement.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"success": True, "message": "Movimiento archivado", "id": movement_id}
