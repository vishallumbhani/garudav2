from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import asyncpg
import csv
from io import StringIO
from fastapi.responses import StreamingResponse
from src.core.config import settings
from src.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/audit", tags=["Audit"])

# Helper to serialize a row (unchanged)
def serialize_audit_row(row):
    r = dict(row)
    return {
        "event_id": r.get("event_id"),
        "tenant_id": str(r["tenant_id"]) if r.get("tenant_id") is not None else None,
        "user_id": str(r["user_id"]) if r.get("user_id") is not None else None,
        "session_id": r.get("session_id"),
        "input_type": r.get("input_type"),
        "endpoint": r.get("endpoint"),
        "decision": r.get("decision"),
        "final_score": r.get("final_score"),
        "policy_action": r.get("policy_action"),
        "policy_reason_codes": r.get("policy_reason_codes") or [],
        "override_applied": r.get("override_applied", False),
        "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
    }


@router.get("/events")
async def list_events(
    tenant_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    decision: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    current_user: dict = Depends(require_role(["admin", "auditor"]))  # Only admin/auditor can view audit
):
    # If user is not platform_admin (i.e., not admin), force filter by their tenant
    if current_user["role"] != "admin":
        tenant_id = current_user.get("tenant_id", "default")

    conn = await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))
    try:
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []

        if tenant_id:
            query += f" AND tenant_id = ${len(params)+1}"
            params.append(tenant_id)

        if user_id:
            query += f" AND user_id = ${len(params)+1}"
            params.append(user_id)

        if decision:
            query += f" AND decision = ${len(params)+1}"
            params.append(decision)

        if start_date:
            query += f" AND created_at >= ${len(params)+1}"
            params.append(start_date)

        if end_date:
            query += f" AND created_at <= ${len(params)+1}"
            params.append(end_date)

        query += f" ORDER BY created_at DESC LIMIT ${len(params)+1}"
        params.append(limit)

        rows = await conn.fetch(query, *params)
        return [serialize_audit_row(row) for row in rows]
    finally:
        await conn.close()


@router.get("/export")
async def export_events(
    format: str = "json",
    tenant_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(require_role(["admin", "auditor"]))
):
    if current_user["role"] != "admin":
        tenant_id = current_user.get("tenant_id", "default")

    conn = await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))
    try:
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []

        if tenant_id:
            query += f" AND tenant_id = ${len(params)+1}"
            params.append(tenant_id)

        if start_date:
            query += f" AND created_at >= ${len(params)+1}"
            params.append(start_date)

        if end_date:
            query += f" AND created_at <= ${len(params)+1}"
            params.append(end_date)

        query += " ORDER BY created_at DESC"
        rows = await conn.fetch(query, *params)

        if format == "csv":
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "event_id", "tenant_id", "user_id", "session_id", "input_type",
                "endpoint", "decision", "final_score", "policy_action",
                "policy_reason_codes", "override_applied", "created_at"
            ])

            for row in rows:
                r = serialize_audit_row(row)
                writer.writerow([
                    r["event_id"],
                    r["tenant_id"],
                    r["user_id"],
                    r["session_id"],
                    r["input_type"],
                    r["endpoint"],
                    r["decision"],
                    r["final_score"],
                    r["policy_action"],
                    r["policy_reason_codes"],
                    r["override_applied"],
                    r["created_at"],
                ])

            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=audit.csv"}
            )

        return [serialize_audit_row(row) for row in rows]
    finally:
        await conn.close()