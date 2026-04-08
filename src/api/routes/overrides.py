
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import asyncpg
from datetime import datetime, timedelta
from src.auth.dependencies import get_current_user, require_role
from src.core.config import settings

router = APIRouter(prefix="/overrides", tags=["Overrides"])

class OverrideRequest(BaseModel):
    request_type: str  # break_glass, temporary_allow, retrieval_unblock
    target_ref: str
    request_reason: str
    duration_minutes: int = 15

class OverrideApprove(BaseModel):
    approve: bool
    expires_at: Optional[datetime] = None

class OverrideResponse(BaseModel):
    id: str
    tenant_id: str
    requester_user_id: str
    override_type: str
    target_ref: str
    reason: str
    status: str
    expires_at: Optional[datetime]
    created_at: datetime

@router.post("/request")
async def request_override(
    req: OverrideRequest,
    identity=Depends(require_role(["admin", "operator"]))
):
    # Require override:request permission
    if "override:request" not in identity["permissions"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    conn = await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))
    try:
        expires_at = datetime.utcnow() + timedelta(minutes=req.duration_minutes)
        row = await conn.fetchrow("""
            INSERT INTO approval_requests (tenant_id, requester_user_id, request_type, target_ref, request_reason, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """, identity["tenant_id"], identity["user_id"], req.request_type, req.target_ref, req.request_reason, expires_at)
        return {"id": str(row["id"]), "status": "pending"}
    finally:
        await conn.close()

@router.post("/{request_id}/approve")
async def approve_override(
    request_id: str,
    approval: OverrideApprove,
    identity=Depends(require_role(["admin", "operator"]))
):
    if "override:approve" not in identity["permissions"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    conn = await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))
    try:
        # Get the request
        req_row = await conn.fetchrow("SELECT * FROM approval_requests WHERE id = $1", request_id)
        if not req_row:
            raise HTTPException(status_code=404, detail="Request not found")
        if req_row["status"] != "pending":
            raise HTTPException(status_code=400, detail="Request already processed")
        if approval.approve:
            status = "approved"
            approved_at = datetime.utcnow()
            expires_at = approval.expires_at or req_row["expires_at"]
            # Create override event
            await conn.execute("""
                INSERT INTO override_events (tenant_id, approval_request_id, requester_user_id, approved_by_user_id, override_type, target_ref, reason, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, req_row["tenant_id"], request_id, req_row["requester_user_id"], identity["user_id"],
               req_row["request_type"], req_row["target_ref"], req_row["request_reason"], expires_at)
        else:
            status = "rejected"
            approved_at = None
        await conn.execute("""
            UPDATE approval_requests SET status = $1, approved_by_user_id = $2, approved_at = $3
            WHERE id = $4
        """, status, identity["user_id"] if approval.approve else None, approved_at, request_id)
        return {"status": status}
    finally:
        await conn.close()

@router.get("/active")
async def list_active_overrides(
    identity=Depends(require_role(["admin", "operator"]))
):
    # Require override:request permission to view (or audit:read)
    if "override:request" not in identity["permissions"] and "audit:read" not in identity["permissions"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    conn = await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))
    try:
        rows = await conn.fetch("""
            SELECT * FROM override_events
            WHERE tenant_id = $1 AND status = 'active' AND (expires_at IS NULL OR expires_at > NOW())
        """, identity["tenant_id"])
        return [OverrideResponse(
            id=str(r["id"]),
            tenant_id=str(r["tenant_id"]),
            requester_user_id=str(r["requester_user_id"]),
            override_type=r["override_type"],
            target_ref=r["target_ref"],
            reason=r["reason"],
            status=r["status"],
            expires_at=r["expires_at"],
            created_at=r["created_at"]
        ) for r in rows]
    finally:
        await conn.close()
