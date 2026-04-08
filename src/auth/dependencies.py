"""
src/auth/dependencies.py
JWT-based dependencies for FastAPI routes.
Replaces X-API-Key with Bearer token auth.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional

from src.services.auth_service import decode_token, get_user_by_id

security = HTTPBearer(auto_error=False)

ROLE_HIERARCHY = {
    "admin": 4,
    "operator": 3,
    "auditor": 2,
    "viewer": 1,
}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Extract and validate JWT token, return user dict."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user = await get_user_by_id(user_id)
    if not user or not user.get("enabled"):
        raise HTTPException(status_code=401, detail="User not found or disabled")
    
    return user


def require_role(roles: List[str]):
    """Dependency factory: require user to have one of the specified roles."""
    async def _check_role(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role", "viewer")
        # Admin can always access everything
        if user_role == "admin":
            return current_user
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role}' is not allowed. Required: {roles}"
            )
        return current_user
    return _check_role


def require_admin():
    """Shortcut dependency for admin-only endpoints."""
    return require_role(["admin"])


def get_tenant_id(current_user: dict = Depends(get_current_user)) -> str:
    """Extract tenant_id from authenticated user."""
    return current_user.get("tenant_id", "default")
