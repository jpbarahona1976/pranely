"""Invite operator router with secure hash (FASE 2.1 FIX 3)

POST /api/v1/invite/{hash:UUID4}
- Redis TTL 24h (86400 seconds) - REAL implementation
- Validates hash from Redis
- Creates membership with role
"""
import logging
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import User, Organization, Membership, UserRole
from app.api.deps import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/invite", tags=["invite"])


# =============================================================================
# Constants
# =============================================================================

INVITE_EXPIRY_SECONDS = 24 * 60 * 60  # 24 hours = 86400 seconds


# =============================================================================
# Pydantic Schemas
# =============================================================================

class InviteHashCreate(BaseModel):
    """Schema to create a new invite hash (admin only)."""
    email: EmailStr
    role: str = Field(..., pattern="^(admin|member|viewer)$")
    organization_id: int


class InviteHashResponse(BaseModel):
    """Response when creating an invite hash."""
    hash: str
    expires_at: datetime
    email: str
    role: str
    invite_url: str


class InviteAcceptRequest(BaseModel):
    """Request to accept an invite and set password."""
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class InviteAcceptResponse(BaseModel):
    """Response after accepting an invite."""
    success: bool
    message: str
    membership_id: int
    organization_name: str


# =============================================================================
# Redis helper functions - FASE 2.1 FIX 3: Real Redis implementation
# =============================================================================

async def store_invite_hash_redis(
    hash_key: str,
    email: str,
    role: str,
    org_id: int,
    ttl: int = INVITE_EXPIRY_SECONDS
) -> bool:
    """
    Store invite hash in Redis with TTL.
    
    FASE 2.1 FIX 3: Real Redis implementation with 24h TTL.
    
    Args:
        hash_key: UUID4 hash key
        email: User email
        role: Role to assign
        org_id: Organization ID
        ttl: Time to live in seconds (default 24h)
    
    Returns:
        True if stored successfully
    """
    try:
        from app.workers.redis_client import get_redis
        
        redis = await get_redis()
        key = f"invite:hash:{hash_key}"
        value = f"{email}:{role}:{org_id}"
        
        # SETEX: Set key with expiration
        await redis.setex(key, ttl, value)
        
        # Also store email lookup for validation
        email_key = f"invite:email:{email}:{org_id}"
        await redis.setex(email_key, ttl, hash_key)
        
        logger.info(
            f"Stored invite hash in Redis: key={key}, ttl={ttl}s, value={value}"
        )
        return True
        
    except Exception as e:
        logger.error(f"Failed to store invite hash in Redis: {e}")
        raise


async def validate_invite_hash_redis(hash_key: str) -> Optional[dict]:
    """
    Validate an invite hash from Redis.
    
    FASE 2.1 FIX 3: Real Redis with TTL validation.
    
    Args:
        hash_key: UUID4 hash to validate
    
    Returns:
        Dict with email, role, org_id if valid and not expired
        None if invalid or expired
    """
    try:
        from app.workers.redis_client import get_redis
        
        redis = await get_redis()
        key = f"invite:hash:{hash_key}"
        
        value = await redis.get(key)
        
        if not value:
            logger.warning(f"Invite hash not found or expired: {hash_key}")
            return None
        
        # Parse value: "email:role:org_id"
        parts = value.decode().split(":") if isinstance(value, bytes) else value.split(":")
        
        if len(parts) != 3:
            logger.error(f"Invalid invite hash value: {value}")
            return None
        
        email, role, org_id_str = parts
        
        return {
            "email": email,
            "role": role,
            "org_id": int(org_id_str),
        }
        
    except Exception as e:
        logger.error(f"Failed to validate invite hash in Redis: {e}")
        return None


async def delete_invite_hash_redis(hash_key: str, email: str = None, org_id: int = None) -> bool:
    """
    Delete invite hash from Redis after use (one-time).
    
    FASE 2.1 FIX 3: Real Redis deletion.
    
    Args:
        hash_key: Hash to delete
        email: Optional email for email key cleanup
        org_id: Optional org_id for email key cleanup
    
    Returns:
        True if deleted successfully
    """
    try:
        from app.workers.redis_client import get_redis
        
        redis = await get_redis()
        
        # Delete main hash key
        key = f"invite:hash:{hash_key}"
        await redis.delete(key)
        
        # Delete email lookup key if provided
        if email and org_id:
            email_key = f"invite:email:{email}:{org_id}"
            await redis.delete(email_key)
        
        logger.info(f"Deleted invite hash from Redis: {hash_key}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete invite hash from Redis: {e}")
        return False


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/create",
    response_model=InviteHashResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create invite hash",
    description="Create a secure invite hash for a new user. Admin/Owner only.",
)
async def create_invite_hash(
    data: InviteHashCreate,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> InviteHashResponse:
    """
    Create a secure invite hash for a new operator.
    
    - **email**: Email of the user to invite
    - **role**: Role to assign (admin, member, viewer)
    - **organization_id**: Target organization
    
    FASE 2.1 FIX 3: Stores hash in Redis with 24h TTL.
    Returns UUID4 hash that expires in 24 hours.
    """
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        # Check if already member of this org
        result = await db.execute(
            select(Membership).where(
                Membership.user_id == existing_user.id,
                Membership.organization_id == data.organization_id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "https://api.pranely.com/errors/invite",
                    "title": "Already member",
                    "status": 400,
                    "detail": "User is already a member of this organization",
                },
            )
    
    # Generate UUID4 hash
    invite_hash = str(uuid.uuid4())
    
    # Store in Redis with 24h TTL (FASE 2.1 FIX 3: Real implementation)
    await store_invite_hash_redis(
        invite_hash,
        data.email,
        data.role,
        data.organization_id,
        INVITE_EXPIRY_SECONDS,
    )
    
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=INVITE_EXPIRY_SECONDS)
    
    logger.info(
        f"Invite hash created: hash={invite_hash}, email={data.email}, "
        f"role={data.role}, org_id={data.organization_id}, ttl={INVITE_EXPIRY_SECONDS}s"
    )
    
    return InviteHashResponse(
        hash=invite_hash,
        expires_at=expires_at,
        email=data.email,
        role=data.role,
        invite_url=f"/invite/{invite_hash}",
    )


@router.post(
    "/{invite_hash}",
    response_model=InviteAcceptResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept invite",
    description="Accept an invite using the hash. Creates user and membership.",
)
async def accept_invite(
    invite_hash: str,
    data: InviteAcceptRequest,
    db: AsyncSession = Depends(get_db),
) -> InviteAcceptResponse:
    """
    Accept an invite and create user account.
    
    - **invite_hash**: UUID4 hash from invite email (24h TTL)
    - **password**: User's new password (min 8 chars)
    - **full_name**: Optional full name
    
    FASE 2.1 FIX 3: Validates hash from Redis, creates user,
    and deletes hash after use (one-time).
    """
    # Validate hash from Redis (FASE 2.1 FIX 3: Real validation)
    invite_data = await validate_invite_hash_redis(invite_hash)
    
    if not invite_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/invite",
                "title": "Invalid or expired invite",
                "status": 400,
                "detail": "This invite link is invalid or has expired. Please request a new invite.",
            },
        )
    
    email = invite_data["email"]
    role = invite_data["role"]
    org_id = invite_data["org_id"]
    
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == email)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        # User exists, just add membership
        result = await db.execute(
            select(Membership).where(
                Membership.user_id == existing_user.id,
                Membership.organization_id == org_id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "type": "https://api.pranely.com/errors/invite",
                    "title": "Already member",
                    "status": 400,
                    "detail": "You are already a member of this organization",
                },
            )
        
        # Add membership
        membership = Membership(
            user_id=existing_user.id,
            organization_id=org_id,
            role=UserRole(role),
        )
        db.add(membership)
        
        logger.info(
            f"Added existing user to org: user_id={existing_user.id}, org_id={org_id}"
        )
    else:
        # Create new user
        from app.core.security import hash_password
        hashed_pw = hash_password(data.password)
        
        new_user = User(
            email=email,
            hashed_password=hashed_pw,
            full_name=data.full_name,
            is_active=True,
        )
        db.add(new_user)
        await db.flush()
        
        # Create membership
        membership = Membership(
            user_id=new_user.id,
            organization_id=org_id,
            role=UserRole(role),
        )
        db.add(membership)
        
        logger.info(
            f"Created new user via invite: email={email}, org_id={org_id}"
        )
    
    await db.commit()
    await db.refresh(membership)
    
    # Get organization name
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    
    # Delete hash from Redis (FASE 2.1 FIX 3: One-time use)
    await delete_invite_hash_redis(invite_hash, email, org_id)
    
    return InviteAcceptResponse(
        success=True,
        message=f"Welcome! You are now a {role} of {org.name if org else 'the organization'}",
        membership_id=membership.id,
        organization_name=org.name if org else "Organization",
    )


@router.get(
    "/{invite_hash}/validate",
    summary="Validate invite hash",
    description="Check if an invite hash is valid and not expired.",
)
async def validate_invite(
    invite_hash: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Validate an invite hash without accepting it."""
    invite_data = await validate_invite_hash_redis(invite_hash)
    
    if not invite_data:
        return {
            "valid": False,
            "message": "Invalid or expired invite",
        }
    
    # Get org name
    org_id = invite_data["org_id"]
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    
    return {
        "valid": True,
        "email": invite_data["email"],
        "role": invite_data["role"],
        "organization": org.name if org else "Unknown",
    }