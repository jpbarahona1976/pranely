"""JWT token utilities using python-jose."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings


class TokenPayload(BaseModel):
    """JWT token payload schema with enhanced claims."""
    sub: str  # user_id
    org_id: Optional[int] = None
    role: Optional[str] = None
    permissions: Optional[list[str]] = None
    exp: Optional[datetime] = None


ALGORITHM = "HS256"


def create_access_token(
    user_id: int,
    org_id: Optional[int] = None,
    role: Optional[str] = None,
    permissions: Optional[list[str]] = None,
) -> str:
    """
    Create a JWT access token with enhanced claims.
    
    Args:
        user_id: User ID to encode in 'sub' claim
        org_id: Organization ID for multi-tenant isolation
        role: User role within organization (owner/admin/member/viewer)
        permissions: List of permission strings
        
    Returns:
        Encoded JWT token string
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    payload = {
        "sub": str(user_id),
        "org_id": org_id,
        "role": role,
        "permissions": permissions or [],
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[TokenPayload]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return TokenPayload(**payload)
    except JWTError:
        return None


def create_org_token(user_id: int, org_id: int, role: str, permissions: list[str]) -> str:
    """
    Create a JWT token for authenticated user with organization context.
    
    Convenience function that ensures org_id, role, and permissions are set.
    """
    return create_access_token(
        user_id=user_id,
        org_id=org_id,
        role=role,
        permissions=permissions,
    )