"""Authentication API endpoints: register and login."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, verify_password
from app.core.tokens import create_access_token
from app.models import Membership, Organization, User, UserRole
from app.api.middleware.tenant import get_permissions_for_role
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
    OrganizationResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user and organization",
    description="Create a new user account with an associated organization (tenant).",
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """Register a new user with their organization."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "Email already registered",
                "status": 400,
                "detail": "Email is already registered",
            },
        )
    
    # Create organization first
    org = Organization(
        name=request.organization_name,
        is_active=True,
    )
    db.add(org)
    await db.flush()  # Get org.id
    
    # Create user with hashed password
    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        is_active=True,
    )
    db.add(user)
    await db.flush()  # Get user.id
    
    # Create membership (owner role)
    membership = Membership(
        user_id=user.id,
        organization_id=org.id,
        role=UserRole.OWNER,
    )
    db.add(membership)
    
    await db.commit()
    await db.refresh(user)
    await db.refresh(org)
    
    return RegisterResponse(
        message="User registered successfully",
        user=UserResponse.model_validate(user),
        organization=OrganizationResponse.model_validate(org),
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login user",
    description="Authenticate user and return JWT token with org context.",
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Login user and return authentication token with org_id, role, and permissions."""
    # Find user by email
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "Invalid credentials",
                "status": 401,
                "detail": "Invalid credentials",
            },
        )
    
    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "Invalid credentials",
                "status": 401,
                "detail": "Invalid credentials",
            },
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "User disabled",
                "status": 403,
                "detail": "User account is disabled",
            },
        )
    
    # Get user's primary organization (first membership)
    result = await db.execute(
        select(Membership)
        .where(Membership.user_id == user.id)
        .order_by(Membership.created_at)
        .limit(1)
    )
    membership = result.scalar_one_or_none()
    
    # Get org details
    org = None
    org_id = None
    role = None
    permissions = []
    
    if membership:
        org_id = membership.organization_id
        role = membership.role.value if membership.role else UserRole.MEMBER.value
        permissions = get_permissions_for_role(role)
        
        # Get organization details
        result = await db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()
    
    # Create access token with enhanced claims (org_id, role, permissions)
    access_token = create_access_token(
        user_id=user.id,
        org_id=org_id,
        role=role,
        permissions=permissions,
    )
    
    return AuthResponse(
        token=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=86400,
        ),
        user=UserResponse.model_validate(user),
        organization=OrganizationResponse.model_validate(org) if org else None,
    )