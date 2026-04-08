from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from src.services.dashboard_service import (
    get_health_status,
    get_recent_scans,
    get_recent_blocks,
    get_trace,
    get_audit_timeline,
    get_engine_outcomes,
    get_policy_hits,
    get_session_behavior,
)
from src.auth.dependencies import get_current_user

router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])

@router.get("/health")
async def health(current_user: dict = Depends(get_current_user)):
    return await get_health_status()

@router.get("/recent-scans")
async def recent_scans(limit: int = 50, current_user: dict = Depends(get_current_user)):
    return await get_recent_scans(limit)

@router.get("/recent-blocks")
async def recent_blocks(limit: int = 50, current_user: dict = Depends(get_current_user)):
    return await get_recent_blocks(limit)

@router.get("/trace/{event_id}")
async def trace(event_id: str, current_user: dict = Depends(get_current_user)):
    data = await get_trace(event_id)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data

@router.get("/timeline")
async def audit_timeline(
    interval: str = "day",
    limit: int = 30,
    current_user: dict = Depends(get_current_user)
):
    return await get_audit_timeline(interval, limit)

@router.get("/engine-outcomes")
async def engine_outcomes(limit: int = 100, current_user: dict = Depends(get_current_user)):
    return await get_engine_outcomes(limit)

@router.get("/policy-hits")
async def policy_hits(limit: int = 50, current_user: dict = Depends(get_current_user)):
    return await get_policy_hits(limit)

@router.get("/session/{session_id}")
async def session_behavior(session_id: str, current_user: dict = Depends(get_current_user)):
    result = await get_session_behavior(session_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result