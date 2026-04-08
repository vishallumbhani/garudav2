"""
src/services/alert_service.py
Alert management: create, list, acknowledge, resolve alerts.
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import text
from src.db.base import AsyncSessionLocal


async def create_alert(
    severity: str,
    title: str,
    description: str = None,
    context: dict = None,
    tenant_id: str = None,
) -> dict:
    alert_id = str(uuid.uuid4())
    query = text("""
        INSERT INTO alerts (id, severity, title, description, context, tenant_id, acknowledged, created_at)
        VALUES (:id, :severity, :title, :description, :context, :tenant_id, false, NOW())
        RETURNING id, severity, title, description, context, tenant_id, acknowledged, created_at
    """)
    import json
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {
            "id": alert_id,
            "severity": severity,
            "title": title,
            "description": description,
            "context": json.dumps(context) if context else None,
            "tenant_id": tenant_id,
        })
        await session.commit()
        row = result.fetchone()
        return dict(row._mapping)


async def list_alerts(
    tenant_id: Optional[str] = None,
    include_acknowledged: bool = False,
    limit: int = 100,
) -> List[dict]:
    conditions = []
    params = {"limit": limit}
    if tenant_id:
        conditions.append("tenant_id = :tenant_id")
        params["tenant_id"] = tenant_id
    if not include_acknowledged:
        conditions.append("acknowledged = false AND resolved_at IS NULL")
    
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    query = text(f"""
        SELECT id, severity, title, description, context, tenant_id,
               acknowledged, acknowledged_by, acknowledged_at, resolved_at, created_at
        FROM alerts {where}
        ORDER BY created_at DESC
        LIMIT :limit
    """)
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, params)
        return [dict(r._mapping) for r in result.fetchall()]


async def acknowledge_alert(alert_id: str, acknowledged_by: str) -> Optional[dict]:
    query = text("""
        UPDATE alerts
        SET acknowledged = true, acknowledged_by = :by, acknowledged_at = NOW()
        WHERE id = :id
        RETURNING id, severity, title, acknowledged, acknowledged_by, acknowledged_at
    """)
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"id": alert_id, "by": acknowledged_by})
        await session.commit()
        row = result.fetchone()
        return dict(row._mapping) if row else None


async def resolve_alert(alert_id: str) -> Optional[dict]:
    query = text("""
        UPDATE alerts
        SET resolved_at = NOW()
        WHERE id = :id
        RETURNING id, severity, title, resolved_at
    """)
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"id": alert_id})
        await session.commit()
        row = result.fetchone()
        return dict(row._mapping) if row else None


async def get_alert_stats(tenant_id: Optional[str] = None) -> dict:
    params = {}
    tenant_filter = ""
    if tenant_id:
        tenant_filter = "AND tenant_id = :tenant_id"
        params["tenant_id"] = tenant_id
    
    query = text(f"""
        SELECT
            COUNT(*) FILTER (WHERE acknowledged = false AND resolved_at IS NULL) AS active,
            COUNT(*) FILTER (WHERE severity = 'critical' AND acknowledged = false) AS critical,
            COUNT(*) FILTER (WHERE severity = 'high' AND acknowledged = false) AS high,
            COUNT(*) FILTER (WHERE acknowledged = true AND resolved_at IS NULL) AS acknowledged,
            COUNT(*) FILTER (WHERE resolved_at IS NOT NULL) AS resolved
        FROM alerts
        WHERE 1=1 {tenant_filter}
    """)
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, params)
        row = result.fetchone()
        if not row:
            return {"active": 0, "critical": 0, "high": 0, "acknowledged": 0, "resolved": 0}
        return dict(row._mapping)
