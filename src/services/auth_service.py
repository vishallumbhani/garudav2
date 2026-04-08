import uuid
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from sqlalchemy import text

from src.db.base import AsyncSessionLocal
from src.core.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        return False
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

ALGORITHM = settings.JWT_ALGORITHM
SECRET_KEY = settings.JWT_SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

async def get_user_by_username(username: str) -> Optional[dict]:
    query = text("SELECT id, username, email, password_hash, role, tenant_id, enabled, must_change_password, created_at, last_login FROM users WHERE username = :username")
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"username": username})
        row = result.fetchone()
        return dict(row._mapping) if row else None

async def get_user_by_id(user_id: str) -> Optional[dict]:
    query = text("SELECT id, username, email, password_hash, role, tenant_id, enabled, must_change_password, created_at, last_login FROM users WHERE id = :id")
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"id": user_id})
        row = result.fetchone()
        return dict(row._mapping) if row else None

async def authenticate_user(username: str, password: str) -> Optional[dict]:
    user = await get_user_by_username(username)
    if not user or not user["enabled"]:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    async with AsyncSessionLocal() as session:
        await session.execute(text("UPDATE users SET last_login = NOW() WHERE id = :id"), {"id": str(user["id"])})
        await session.commit()
    return user

async def create_user(username: str, password: str, role: str = "viewer", tenant_id: str = "default", email: str = None) -> dict:
    password_hash = hash_password(password)
    user_id = str(uuid.uuid4())
    query = text("""INSERT INTO users (id, username, email, password_hash, role, tenant_id, enabled, created_at)
        VALUES (:id, :username, :email, :password_hash, :role, :tenant_id, true, NOW())
        RETURNING id, username, email, role, tenant_id, enabled, created_at, last_login""")
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, {"id": user_id, "username": username, "email": email, "password_hash": password_hash, "role": role, "tenant_id": tenant_id})
        await session.commit()
        row = result.fetchone()
        return dict(row._mapping)

async def update_user(user_id: str, update_data: dict) -> Optional[dict]:
    if "password" in update_data:
        update_data["password_hash"] = hash_password(update_data.pop("password"))
    set_clause = ", ".join([f"{k} = :{k}" for k in update_data.keys()])
    query = text(f"UPDATE users SET {set_clause}, updated_at = NOW() WHERE id = :id RETURNING id, username, email, role, tenant_id, enabled, created_at, last_login")
    update_data["id"] = user_id
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, update_data)
        await session.commit()
        row = result.fetchone()
        return dict(row._mapping) if row else None

async def delete_user(user_id: str) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        await session.commit()
        return result.rowcount > 0

async def list_users(tenant_id: Optional[str] = None) -> list:
    if tenant_id:
        query = text("SELECT id, username, email, role, tenant_id, enabled, created_at, last_login FROM users WHERE tenant_id = :tenant_id ORDER BY created_at DESC")
        params = {"tenant_id": tenant_id}
    else:
        query = text("SELECT id, username, email, role, tenant_id, enabled, created_at, last_login FROM users ORDER BY created_at DESC")
        params = {}
    async with AsyncSessionLocal() as session:
        result = await session.execute(query, params)
        return [dict(r._mapping) for r in result.fetchall()]

async def reset_user_password(user_id: str, new_password: str) -> bool:
    password_hash = hash_password(new_password)
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("UPDATE users SET password_hash = :ph, must_change_password = true, updated_at = NOW() WHERE id = :id"), {"ph": password_hash, "id": user_id})
        await session.commit()
        return result.rowcount > 0
