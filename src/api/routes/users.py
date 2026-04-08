"""
src/api/routes/users.py  (or add to admin.py)
User management endpoints - admin only.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from src.schemas.auth import UserCreate, UserUpdate, UserOut, PasswordReset
from src.services.auth_service import (
    create_user, update_user, delete_user, list_users,
    reset_user_password, get_user_by_id
)
from src.auth.dependencies import require_role

router = APIRouter(prefix="/v1/admin/users", tags=["users"])
admin_only = require_role(["admin"])


@router.get("", response_model=list[UserOut])
async def get_users(
    tenant_id: Optional[str] = None,
    _: dict = Depends(admin_only),
):
    users = await list_users(tenant_id=tenant_id)
    return [
        UserOut(
            id=str(u["id"]),
            username=u["username"],
            email=u.get("email"),
            role=u["role"],
            tenant_id=u.get("tenant_id"),
            enabled=u["enabled"],
            created_at=u["created_at"],
            last_login=u.get("last_login"),
        )
        for u in users
    ]


@router.post("", response_model=UserOut, status_code=201)
async def create_new_user(
    body: UserCreate,
    _: dict = Depends(admin_only),
):
    try:
        user = await create_user(
            username=body.username,
            password=body.password,
            role=body.role,
            tenant_id=body.tenant_id or "default",
            email=body.email,
        )
        return UserOut(
            id=str(user["id"]),
            username=user["username"],
            email=user.get("email"),
            role=user["role"],
            tenant_id=user.get("tenant_id"),
            enabled=user["enabled"],
            created_at=user["created_at"],
            last_login=user.get("last_login"),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{user_id}", response_model=UserOut)
async def update_existing_user(
    user_id: str,
    body: UserUpdate,
    _: dict = Depends(admin_only),
):
    update_data = body.model_dump(exclude_unset=True)
    user = await update_user(user_id, update_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(
        id=str(user["id"]),
        username=user["username"],
        email=user.get("email"),
        role=user["role"],
        tenant_id=user.get("tenant_id"),
        enabled=user["enabled"],
        created_at=user["created_at"],
        last_login=user.get("last_login"),
    )


@router.delete("/{user_id}")
async def remove_user(
    user_id: str,
    _: dict = Depends(admin_only),
):
    success = await delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: str,
    body: PasswordReset,
    _: dict = Depends(admin_only),
):
    success = await reset_user_password(user_id, body.new_password)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Password reset successfully. User must change on next login."}
