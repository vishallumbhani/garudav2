import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import text
from src.db.base import AsyncSessionLocal

# ========== Rule Management ==========
async def list_rules(engine: Optional[str] = None) -> List[dict]:
    query = text("SELECT * FROM rules WHERE 1=1")
    params = {}
    if engine:
        query = text("SELECT * FROM rules WHERE engine = :engine")
        params["engine"] = engine
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, params)
        rows = result.fetchall()
        return [dict(r._mapping) for r in rows]

async def create_rule(rule_data: dict) -> dict:
    query = text("""
        INSERT INTO rules (engine, name, conditions, action, enabled, priority, created_at, updated_at)
        VALUES (:engine, :name, :conditions, :action, :enabled, :priority, NOW(), NOW())
        RETURNING *
    """)
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, rule_data)
        await session.commit()
        row = result.fetchone()
        return dict(row._mapping)

async def update_rule(rule_id: int, update_data: dict) -> Optional[dict]:
    set_clause = ", ".join([f"{k} = :{k}" for k in update_data.keys()])
    query = text(f"UPDATE rules SET {set_clause}, updated_at = NOW() WHERE id = :id RETURNING *")
    update_data["id"] = rule_id
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, update_data)
        await session.commit()
        row = result.fetchone()
        return dict(row._mapping) if row else None

async def delete_rule(rule_id: int) -> bool:
    query = text("DELETE FROM rules WHERE id = :id")
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"id": rule_id})
        await session.commit()
        return result.rowcount > 0

# ========== Policy Management ==========
async def list_policies(tenant_id: Optional[str] = None) -> List[dict]:
    query = text("SELECT * FROM policies WHERE 1=1")
    params = {}
    if tenant_id:
        query = text("SELECT * FROM policies WHERE tenant_id = :tenant_id")
        params["tenant_id"] = tenant_id
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, params)
        rows = result.fetchall()
        return [dict(r._mapping) for r in rows]

async def update_policy(policy_key: str, update_data: dict) -> Optional[dict]:
    set_clause = ", ".join([f"{k} = :{k}" for k in update_data.keys()])
    query = text(f"UPDATE policies SET {set_clause} WHERE policy_key = :policy_key RETURNING *")
    update_data["policy_key"] = policy_key
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, update_data)
        await session.commit()
        row = result.fetchone()
        return dict(row._mapping) if row else None

# ========== Tenant Config ==========
async def get_tenant_config(tenant_id: str) -> Optional[dict]:
    query = text("SELECT * FROM tenant_configs WHERE tenant_id = :tenant_id")
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"tenant_id": tenant_id})
        row = result.fetchone()
        return dict(row._mapping) if row else None

async def update_tenant_config(tenant_id: str, update_data: dict) -> Optional[dict]:
    set_clause = ", ".join([f"{k} = :{k}" for k in update_data.keys()])
    query = text(f"UPDATE tenant_configs SET {set_clause} WHERE tenant_id = :tenant_id RETURNING *")
    update_data["tenant_id"] = tenant_id
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, update_data)
        await session.commit()
        row = result.fetchone()
        return dict(row._mapping) if row else None

# ========== API Key Management ==========
async def list_api_keys(tenant_id: Optional[str] = None) -> List[dict]:
    query = text("SELECT id, key_prefix, tenant_id, created_at, last_used, expires_at, enabled FROM api_keys")
    params = {}
    if tenant_id:
        query = text("SELECT ... WHERE tenant_id = :tenant_id")
        params["tenant_id"] = tenant_id
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, params)
        rows = result.fetchall()
        return [dict(r._mapping) for r in rows]

async def create_api_key(key_data: dict) -> dict:
    raw_key = secrets.token_urlsafe(32)
    key_prefix = raw_key[:8]
    hashed = secrets.token_urlsafe(64)  # In production, hash properly
    expires_at = datetime.utcnow() + timedelta(days=key_data.get("expires_days", 90))
    query = text("""
        INSERT INTO api_keys (key_prefix, hashed_key, tenant_id, created_at, expires_at, enabled)
        VALUES (:key_prefix, :hashed_key, :tenant_id, NOW(), :expires_at, True)
        RETURNING id, key_prefix, tenant_id, created_at, expires_at
    """)
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {
            "key_prefix": key_prefix,
            "hashed_key": hashed,
            "tenant_id": key_data["tenant_id"],
            "expires_at": expires_at,
        })
        await session.commit()
        row = result.fetchone()
        return {"api_key": raw_key, **dict(row._mapping)}

async def revoke_api_key(key_id: int) -> bool:
    query = text("UPDATE api_keys SET enabled = False WHERE id = :id")
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"id": key_id})
        await session.commit()
        return result.rowcount > 0