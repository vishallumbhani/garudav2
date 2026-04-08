"""
src/api/routes/auth.py
JWT auth endpoints: /auth/login, /auth/refresh, /auth/logout, /auth/me
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, UserOut, ChangePassword
from src.services.auth_service import (
    authenticate_user, create_access_token, create_refresh_token,
    decode_token, get_user_by_id
)
from src.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload.get("sub")
    user = await get_user_by_id(user_id)
    if not user or not user["enabled"]:
        raise HTTPException(status_code=401, detail="User not found or disabled")
    return user


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = await authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    token_data = {
        "sub": str(user["id"]),
        "username": user["username"],
        "role": user["role"],
        "tenant_id": user["tenant_id"],
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"sub": str(user["id"])})
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest):
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = payload.get("sub")
    user = await get_user_by_id(user_id)
    if not user or not user["enabled"]:
        raise HTTPException(status_code=401, detail="User not found or disabled")
    token_data = {
        "sub": str(user["id"]),
        "username": user["username"],
        "role": user["role"],
        "tenant_id": user["tenant_id"],
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"sub": str(user["id"])})
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)):
    return UserOut(
        id=str(current_user["id"]),
        username=current_user["username"],
        email=current_user.get("email"),
        role=current_user["role"],
        tenant_id=current_user.get("tenant_id"),
        enabled=current_user["enabled"],
        created_at=current_user["created_at"],
        last_login=current_user.get("last_login"),
    )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    # In production, add token to a blacklist in Redis
    return {"message": "Logged out successfully"}
