
import hashlib
import secrets
import asyncpg
from src.core.config import settings

async def generate_api_key(tenant_id: str, user_id: str = None, label: str = None, expires_at=None):
    prefix = "garuda_live_"
    random_part = secrets.token_urlsafe(24)
    raw_key = prefix + random_part
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = prefix
    conn = await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))
    try:
        await conn.execute("""
            INSERT INTO api_keys (tenant_id, user_id, key_prefix, key_hash, label, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, tenant_id, user_id, key_prefix, key_hash, label, expires_at)
    finally:
        await conn.close()
    return raw_key

async def validate_api_key(raw_key: str):
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    conn = await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))
    try:
        row = await conn.fetchrow("""
            SELECT ak.*, u.role_id, r.role_key
            FROM api_keys ak
            LEFT JOIN users u ON ak.user_id = u.id
            LEFT JOIN roles r ON u.role_id = r.id
            WHERE ak.key_hash = $1 AND ak.is_active = true
        """, key_hash)
        if row and (row["expires_at"] is None or row["expires_at"] > datetime.now()):
            await conn.execute("UPDATE api_keys SET last_used_at = NOW() WHERE id = $1", row["id"])
            return row
        return None
    finally:
        await conn.close()
