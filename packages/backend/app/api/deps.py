"""Authentication dependencies (JWT verification, current user)."""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.tokens import decode_token
from app.models import User

# Use auto_error=False so we can handle the 401 ourselves
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "No token",
                "status": 401,
                "detail": "Authentication required",
            },
        )
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "Invalid token",
                "status": 401,
                "detail": "Token is invalid or expired",
            },
        )
    
    try:
        user_id = int(payload.sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "Invalid token payload",
                "status": 401,
                "detail": "Token contains invalid user ID",
            },
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "type": "https://api.pranely.com/errors/auth",
                "title": "User not found",
                "status": 401,
                "detail": "User associated with token no longer exists",
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
    
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Get current user if authenticated, otherwise None."""
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None