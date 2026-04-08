#!/usr/bin/env python3
"""
Phase 4A: Multi‑tenancy and authentication (safe – does not modify scan endpoints).
- Creates tables and seeds data.
- Adds auth modules and login endpoint.
- Leaves existing endpoints untouched.
"""

import os
import asyncio
import asyncpg
import bcrypt
import jwt
from datetime import datetime, timedelta
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://garuda:change_this_local_password@localhost:5432/garuda")
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
        print("✅ Tables created/verified.")
    finally:
        await conn.close()

async def seed_data():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
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

        # platform_admin gets all
        for perm_id in perm_ids.values():
            await conn.execute("""
                INSERT INTO role_permissions (role_id, permission_id) VALUES ($1, $2) ON CONFLICT DO NOTHING
            """, role_ids["platform_admin"], perm_id)
        # tenant_admin gets most
        for perm_key in ["scan:text", "scan:file", "rag:query", "tenant:read", "tenant:update", "policy:read", "policy:update", "override:request", "override:approve", "audit:read"]:
            await conn.execute("""
                INSERT INTO role_permissions (role_id, permission_id) VALUES ($1, $2) ON CONFLICT DO NOTHING
            """, role_ids["tenant_admin"], perm_ids[perm_key])
        # analyst gets scan, rag, audit:read, override:request
        for perm_key in ["scan:text", "scan:file", "rag:query", "audit:read", "override:request"]:
            await conn.execute("""
                INSERT INTO role_permissions (role_id, permission_id) VALUES ($1, $2) ON CONFLICT DO NOTHING
            """, role_ids["analyst"], perm_ids[perm_key])
        # viewer gets scan:text, rag:query, audit:read
        for perm_key in ["scan:text", "rag:query", "audit:read"]:
            await conn.execute("""
                INSERT INTO role_permissions (role_id, permission_id) VALUES ($1, $2) ON CONFLICT DO NOTHING
            """, role_ids["viewer"], perm_ids[perm_key])
        # customer gets scan:text, rag:query
        for perm_key in ["scan:text", "rag:query"]:
            await conn.execute("""
                INSERT INTO role_permissions (role_id, permission_id) VALUES ($1, $2) ON CONFLICT DO NOTHING
            """, role_ids["customer"], perm_ids[perm_key])
        # service_account gets scan:text, scan:file
        for perm_key in ["scan:text", "scan:file"]:
            await conn.execute("""
                INSERT INTO role_permissions (role_id, permission_id) VALUES ($1, $2) ON CONFLICT DO NOTHING
            """, role_ids["service_account"], perm_ids[perm_key])

        # Create platform admin user (password: admin123)
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

def create_auth_modules():
    os.makedirs("src/auth", exist_ok=True)
    # jwt_service.py
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
    # api_key_service.py (simplified for now)
    with open("src/auth/api_key_service.py", "w") as f:
        f.write('''
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
''')
    # dependencies.py (no automatic protection of existing endpoints)
    with open("src/auth/dependencies.py", "w") as f:
        f.write('''
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.auth.jwt_service import decode_token
from src.auth.api_key_service import validate_api_key
import asyncpg
from src.core.config import settings

security = HTTPBearer(auto_error=False)

async def get_identity_context(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    payload = decode_token(token)
    if payload:
        return {
            "auth_type": "jwt",
            "user_id": payload.get("user_id"),
            "tenant_id": payload.get("tenant_id"),
            "role": payload.get("role"),
            "permissions": payload.get("permissions", []),
        }
    key_info = await validate_api_key(token)
    if key_info:
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
''')
    print("✅ Auth modules created.")

def add_login_endpoint():
    # Create auth.py route
    auth_route = Path("src/api/routes/auth.py")
    if not auth_route.exists():
        auth_route.write_text('''
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import asyncpg
import bcrypt
from src.auth.jwt_service import create_access_token
from src.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    role: str

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    conn = await asyncpg.connect(settings.DATABASE_URL.replace("+asyncpg", ""))
    try:
        row = await conn.fetchrow("""
            SELECT u.id, u.tenant_id, u.email, u.password_hash, r.role_key
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.email = $1 AND u.is_active = true
        """, req.email)
        if not row:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not bcrypt.checkpw(req.password.encode(), row["password_hash"].encode()):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        perms = await conn.fetch("""
            SELECT p.permission_key
            FROM role_permissions rp
            JOIN permissions p ON rp.permission_id = p.id
            WHERE rp.role_id = (SELECT role_id FROM users WHERE id = $1)
        """, row["id"])
        permissions = [p["permission_key"] for p in perms]
        token_data = {
            "user_id": str(row["id"]),
            "tenant_id": str(row["tenant_id"]),
            "role": row["role_key"],
            "permissions": permissions,
        }
        access_token = create_access_token(token_data)
        return LoginResponse(
            access_token=access_token,
            tenant_id=str(row["tenant_id"]),
            role=row["role_key"]
        )
    finally:
        await conn.close()
''')
    # Add router to main.py if not already
    main_path = Path("src/api/main.py")
    content = main_path.read_text()
    if "from src.api.routes import auth" not in content:
        content = content.replace(
            "from src.api.routes import scan_text, scan_file",
            "from src.api.routes import scan_text, scan_file, auth"
        )
        content = content.replace(
            "app.include_router(scan_file.router)",
            "app.include_router(scan_file.router)\napp.include_router(auth.router)"
        )
        main_path.write_text(content)
        print("✅ Added auth router to main.py.")
    else:
        print("Auth router already present.")

async def main():
    print("Phase 4A Setup (safe mode – no endpoint protection)")
    await create_tables()
    await seed_data()
    create_auth_modules()
    add_login_endpoint()
    print("Phase 4A complete. Restart the server and test login.")
    print("Existing scan endpoints remain unprotected (Phase 3).")

if __name__ == "__main__":
    asyncio.run(main())
