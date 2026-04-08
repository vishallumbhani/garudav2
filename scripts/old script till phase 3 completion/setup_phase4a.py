#!/usr/bin/env python3
"""
Phase 4A: Multi‑tenancy, RBAC, and authentication foundation.
Creates tables, seeds data, and adds authentication to the API.
"""

import os
import sys
import asyncio
import asyncpg
from pathlib import Path
import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# ----------------------------------------------------------------------
# Database setup
# ----------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://garuda:change_this_local_password@localhost:5432/garuda")
# Convert to asyncpg format (remove +asyncpg if present)
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

async def create_tables():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Tenants
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_key VARCHAR(100) UNIQUE NOT NULL,
                tenant_name VARCHAR(200) NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'active',
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tenant_configs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                risk_mode VARCHAR(30) NOT NULL DEFAULT 'standard',
                block_threshold INTEGER NOT NULL DEFAULT 80,
                challenge_threshold INTEGER NOT NULL DEFAULT 60,
                enable_rag BOOLEAN NOT NULL DEFAULT TRUE,
                enable_ocr BOOLEAN NOT NULL DEFAULT TRUE,
                enable_code_scan BOOLEAN NOT NULL DEFAULT TRUE,
                data_policy_level VARCHAR(30) NOT NULL DEFAULT 'standard',
                default_action VARCHAR(30) NOT NULL DEFAULT 'monitor',
                strict_tenant BOOLEAN NOT NULL DEFAULT FALSE,
                config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(tenant_id)
            )
        """)

        # Roles and permissions
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                role_key VARCHAR(50) UNIQUE NOT NULL,
                role_name VARCHAR(100) NOT NULL,
                description TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                permission_key VARCHAR(100) UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS role_permissions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
                permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
                UNIQUE(role_id, permission_id)
            )
        """)

        # Users and API keys
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                email VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                password_hash TEXT,
                role_id UUID NOT NULL REFERENCES roles(id),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(tenant_id, email)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                key_prefix VARCHAR(20) NOT NULL,
                key_hash TEXT NOT NULL,
                label VARCHAR(100),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                expires_at TIMESTAMP NULL,
                last_used_at TIMESTAMP NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)

        # Additional tables for later phases (create if not exist to be ready)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS policies (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                policy_key VARCHAR(100) UNIQUE NOT NULL,
                policy_name VARCHAR(200) NOT NULL,
                policy_level VARCHAR(30) NOT NULL,
                tenant_id UUID NULL REFERENCES tenants(id) ON DELETE CASCADE,
                applies_to JSONB NOT NULL DEFAULT '[]'::jsonb,
                conditions_json JSONB NOT NULL,
                action VARCHAR(30) NOT NULL,
                severity VARCHAR(30) NOT NULL DEFAULT 'medium',
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS policy_overrides (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                policy_id UUID NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
                tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                override_action VARCHAR(30) NOT NULL,
                override_reason TEXT,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(policy_id, tenant_id)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS approval_requests (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                requester_user_id UUID NOT NULL REFERENCES users(id),
                request_type VARCHAR(50) NOT NULL,
                target_ref VARCHAR(255),
                request_reason TEXT NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'pending',
                approved_by_user_id UUID NULL REFERENCES users(id),
                approved_at TIMESTAMP NULL,
                expires_at TIMESTAMP NULL,
                metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS override_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                approval_request_id UUID NULL REFERENCES approval_requests(id),
                requester_user_id UUID NOT NULL REFERENCES users(id),
                approved_by_user_id UUID NULL REFERENCES users(id),
                override_type VARCHAR(50) NOT NULL,
                target_ref VARCHAR(255),
                reason TEXT NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'active',
                expires_at TIMESTAMP NULL,
                metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS retrieval_audit_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                user_id UUID NULL REFERENCES users(id),
                query_text TEXT,
                user_role VARCHAR(50),
                total_chunks INTEGER NOT NULL DEFAULT 0,
                allowed_chunks INTEGER NOT NULL DEFAULT 0,
                blocked_chunks INTEGER NOT NULL DEFAULT 0,
                reasons_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                trace_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)

        print("✅ Tables created/verified.")
    finally:
        await conn.close()

async def seed_data():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Insert default tenant
        tenant_id = await conn.fetchval("""
            INSERT INTO tenants (tenant_key, tenant_name) VALUES ('default', 'Default Tenant')
            ON CONFLICT (tenant_key) DO UPDATE SET tenant_name = EXCLUDED.tenant_name
            RETURNING id
        """)
        await conn.execute("""
            INSERT INTO tenant_configs (tenant_id, risk_mode, block_threshold, challenge_threshold, strict_tenant)
            VALUES ($1, 'standard', 80, 60, false)
            ON CONFLICT (tenant_id) DO UPDATE SET risk_mode = EXCLUDED.risk_mode
        """, tenant_id)

        # Insert roles
        roles = {
            "platform_admin": "Platform Administrator",
            "tenant_admin": "Tenant Administrator",
            "analyst": "Security Analyst",
            "customer": "Customer User",
            "viewer": "Read-Only Viewer",
            "service_account": "Service Account"
        }
        role_ids = {}
        for key, name in roles.items():
            role_id = await conn.fetchval("""
                INSERT INTO roles (role_key, role_name) VALUES ($1, $2)
                ON CONFLICT (role_key) DO UPDATE SET role_name = EXCLUDED.role_name
                RETURNING id
            """, key, name)
            role_ids[key] = role_id

        # Insert permissions
        permissions = [
            ("scan:text", "Scan text inputs"),
            ("scan:file", "Scan file uploads"),
            ("rag:query", "Perform RAG queries"),
            ("tenant:read", "Read tenant configuration"),
            ("tenant:update", "Update tenant configuration"),
            ("policy:read", "Read policies"),
            ("policy:update", "Create/update policies"),
            ("override:request", "Request overrides"),
            ("override:approve", "Approve overrides"),
            ("audit:read", "Read audit logs"),
            ("admin:full", "Full administrative access"),
        ]
        perm_ids = {}
        for key, desc in permissions:
            perm_id = await conn.fetchval("""
                INSERT INTO permissions (permission_key, description) VALUES ($1, $2)
                ON CONFLICT (permission_key) DO UPDATE SET description = EXCLUDED.description
                RETURNING id
            """, key, desc)
            perm_ids[key] = perm_id

        # Assign permissions to roles
        # platform_admin gets all
        for perm_id in perm_ids.values():
            await conn.execute("""
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES ($1, $2) ON CONFLICT DO NOTHING
            """, role_ids["platform_admin"], perm_id)

        # tenant_admin gets everything except admin:full (maybe)
        for perm_key in ["scan:text", "scan:file", "rag:query", "tenant:read", "tenant:update", "policy:read", "policy:update", "override:request", "override:approve", "audit:read"]:
            await conn.execute("""
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES ($1, $2) ON CONFLICT DO NOTHING
            """, role_ids["tenant_admin"], perm_ids[perm_key])

        # analyst gets scan, rag, audit:read, override:request
        for perm_key in ["scan:text", "scan:file", "rag:query", "audit:read", "override:request"]:
            await conn.execute("""
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES ($1, $2) ON CONFLICT DO NOTHING
            """, role_ids["analyst"], perm_ids[perm_key])

        # viewer gets only scan:text, rag:query (maybe limited), audit:read (own tenant)
        for perm_key in ["scan:text", "rag:query", "audit:read"]:
            await conn.execute("""
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES ($1, $2) ON CONFLICT DO NOTHING
            """, role_ids["viewer"], perm_ids[perm_key])

        # customer gets scan:text, rag:query (tenant-scoped)
        for perm_key in ["scan:text", "rag:query"]:
            await conn.execute("""
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES ($1, $2) ON CONFLICT DO NOTHING
            """, role_ids["customer"], perm_ids[perm_key])

        # service_account gets scan:text, scan:file (API-only)
        for perm_key in ["scan:text", "scan:file"]:
            await conn.execute("""
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES ($1, $2) ON CONFLICT DO NOTHING
            """, role_ids["service_account"], perm_ids[perm_key])

        # Create a platform admin user (password: admin123)
        admin_email = "admin@garuda.local"
        admin_password = "admin123"
        password_hash = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt()).decode()
        await conn.execute("""
            INSERT INTO users (tenant_id, email, full_name, password_hash, role_id)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (tenant_id, email) DO UPDATE SET password_hash = EXCLUDED.password_hash, role_id = EXCLUDED.role_id
        """, tenant_id, admin_email, "Platform Admin", password_hash, role_ids["platform_admin"])

        print("✅ Seed data inserted.")
    finally:
        await conn.close()

# ----------------------------------------------------------------------
# Authentication modules
# ----------------------------------------------------------------------
# These will be integrated into the FastAPI app.
# We'll create the necessary files in src/auth/

def create_auth_modules():
    os.makedirs("src/auth", exist_ok=True)
    # JWT service
    with open("src/auth/jwt_service.py", "w") as f:
        f.write('''
import jwt
from datetime import datetime, timedelta
from src.core.config import settings

SECRET_KEY = settings.GARUDA_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
''')
    # API key service
    with open("src/auth/api_key_service.py", "w") as f:
        f.write('''
import hashlib
import secrets
import asyncpg
from src.core.config import settings

async def generate_api_key(tenant_id: str, user_id: str = None, label: str = None, expires_at=None):
    # Generate a random key: garuda_live_<random>
    prefix = "garuda_live_"
    random_part = secrets.token_urlsafe(24)
    raw_key = prefix + random_part
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = prefix
    # Store in DB
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
            # Update last_used
            await conn.execute("UPDATE api_keys SET last_used_at = NOW() WHERE id = $1", row["id"])
            return row
        return None
    finally:
        await conn.close()
''')
    # Dependencies
    with open("src/auth/dependencies.py", "w") as f:
        f.write('''
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.auth.jwt_service import decode_token
from src.auth.api_key_service import validate_api_key
import asyncpg
from src.core.config import settings

security = HTTPBearer(auto_error=False)

async def get_identity_context(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    # Try JWT first
    payload = decode_token(token)
    if payload:
        # JWT payload should contain user_id, tenant_id, role
        return {
            "auth_type": "jwt",
            "user_id": payload.get("user_id"),
            "tenant_id": payload.get("tenant_id"),
            "role": payload.get("role"),
            "permissions": payload.get("permissions", []),
        }
    # Try API key
    key_info = await validate_api_key(token)
    if key_info:
        # key_info has tenant_id, user_id, role_key, etc.
        # We need to fetch permissions for the role
        conn = await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))
        try:
            perms = await conn.fetch("""
                SELECT p.permission_key
                FROM role_permissions rp
                JOIN permissions p ON rp.permission_id = p.id
                WHERE rp.role_id = $1
            """, key_info["role_id"])
            permissions = [p["permission_key"] for p in perms]
        finally:
            await conn.close()
        return {
            "auth_type": "api_key",
            "user_id": key_info["user_id"],
            "tenant_id": key_info["tenant_id"],
            "role": key_info["role_key"],
            "permissions": permissions,
        }
    raise HTTPException(status_code=401, detail="Invalid token")

def require_permission(permission_key: str):
    async def checker(identity=Depends(get_identity_context)):
        if permission_key not in identity["permissions"]:
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission_key}")
        return identity
    return checker

def require_tenant_access(tenant_id: str):
    async def checker(identity=Depends(get_identity_context)):
        if identity["role"] != "platform_admin" and identity["tenant_id"] != tenant_id:
            raise HTTPException(status_code=403, detail="Tenant isolation violation")
        return identity
    return checker
''')
    print("✅ Auth modules created.")

# ----------------------------------------------------------------------
# Integration with existing scan endpoints
# ----------------------------------------------------------------------
def patch_scan_endpoints():
    # We'll modify src/api/routes/scan_text.py and scan_file.py to add dependencies.
    # Since these files already exist, we'll insert the dependency into the endpoint functions.
    # We'll use a backup and then patch.
    import re
    from pathlib import Path

    scan_text_path = Path("src/api/routes/scan_text.py")
    if scan_text_path.exists():
        content = scan_text_path.read_text()
        # Add import for dependencies if not already
        if "from src.auth.dependencies import require_permission" not in content:
            content = content.replace("from fastapi import APIRouter", "from fastapi import APIRouter, Depends\nfrom src.auth.dependencies import require_permission")
        # Add dependency to the endpoint
        # The function definition is `async def scan_text_endpoint(request: TextScanRequest):`
        # We need to add `, identity = Depends(require_permission("scan:text"))`
        content = re.sub(r'(async def scan_text_endpoint\(request: TextScanRequest\))', r'\1, identity = Depends(require_permission("scan:text"))', content)
        scan_text_path.write_text(content)
        print("Patched scan_text endpoint with permission check.")
    else:
        print("scan_text.py not found, skipping.")

    scan_file_path = Path("src/api/routes/scan_file.py")
    if scan_file_path.exists():
        content = scan_file_path.read_text()
        if "from src.auth.dependencies import require_permission" not in content:
            content = content.replace("from fastapi import APIRouter", "from fastapi import APIRouter, Depends\nfrom src.auth.dependencies import require_permission")
        content = re.sub(r'(async def scan_file_endpoint\(file: UploadFile = File\(...\), tenant_id: str = Form\("default"\), user_id: Optional\[str\] = Form\(None\), session_id: Optional\[str\] = Form\(None\), source: str = Form\("api"\)\))', r'\1, identity = Depends(require_permission("scan:file"))', content)
        scan_file_path.write_text(content)
        print("Patched scan_file endpoint with permission check.")
    else:
        print("scan_file.py not found, skipping.")

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
async def main():
    print("Setting up Phase 4A...")
    await create_tables()
    await seed_data()
    create_auth_modules()
    patch_scan_endpoints()
    print("Phase 4A setup complete. Restart the server and test authentication.")

if __name__ == "__main__":
    asyncio.run(main())
