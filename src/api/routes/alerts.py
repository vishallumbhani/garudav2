"""
src/api/routes/alerts.py
Alert management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel

from src.services.alert_service import (
    list_alerts, acknowledge_alert, resolve_alert, get_alert_stats
)
from src.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/v1/alerts", tags=["alerts"])


class AcknowledgeRequest(BaseModel):
    alert_id: str


@router.get("")
async def get_alerts(
    include_acknowledged: bool = False,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
):
    tenant_id = current_user.get("tenant_id")
    # Admins see all tenants
    if current_user.get("role") == "admin":
        tenant_id = None
    return await list_alerts(tenant_id=tenant_id, include_acknowledged=include_acknowledged, limit=limit)


@router.get("/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    tenant_id = current_user.get("tenant_id")
    if current_user.get("role") == "admin":
        tenant_id = None
    return await get_alert_stats(tenant_id=tenant_id)


@router.post("/{alert_id}/acknowledge")
async def acknowledge(
    alert_id: str,
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    result = await acknowledge_alert(alert_id, current_user["username"])
    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")
    return result


@router.post("/{alert_id}/resolve")
async def resolve(
    alert_id: str,
    current_user: dict = Depends(require_role(["admin", "operator"])),
):
    result = await resolve_alert(alert_id)
    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")
    return result
