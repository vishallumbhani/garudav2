#!/usr/bin/env python3
"""
Fix DB session conflict in audit logging.
- Update base.py to use async_sessionmaker
- Rewrite audit_service.py to use its own session
- Update scan_service.py to call log_audit without db argument
"""

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

def write_file(path, content):
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"Written: {file_path}")

# 1. Update base.py
new_base = '''from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from src.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

Base = declarative_base()
'''
write_file("src/db/base.py", new_base)

# 2. Update audit_service.py
new_audit = '''import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.db.base import AsyncSessionLocal
from src.db.models import AuditLog

logger = logging.getLogger(__name__)


async def log_audit(event_data: dict):
    """
    Write audit entry to JSONL file and database.
    Uses a dedicated DB session to avoid async session conflicts.
    """
    # Write to JSONL file first
    log_path = Path("./logs/audit.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event_data, ensure_ascii=False, default=str) + "\\n")

    # Write to database using a fresh session
    try:
        async with AsyncSessionLocal() as db:
            audit = AuditLog(
                event_id=event_data["event_id"],
                tenant_id=event_data.get("tenant_id"),
                user_id=event_data.get("user_id"),
                session_id=event_data.get("session_id"),
                input_type=event_data["input_type"],
                decision=event_data["decision"],
                final_score=event_data["final_score"],
                engine_results=event_data["engine_results"],
                trace=event_data["trace"],
                created_at=datetime.now(timezone.utc),
            )
            db.add(audit)
            await db.commit()
    except Exception as e:
        logger.error("Failed to write audit log to DB: %s", e, exc_info=True)
        logger.warning("Audit log saved only to file, DB error.")
'''
write_file("src/services/audit_service.py", new_audit)

# 3. Update scan_service.py to remove db argument in log_audit call
scan_path = "src/services/scan_service.py"
with open(scan_path, "r") as f:
    scan_content = f.read()

# Replace the line that calls log_audit
# The old pattern: await log_audit(db, audit_data)
# New pattern: await log_audit(audit_data)
# Also remove the db context manager that is no longer needed.
# We'll find the block where audit_data is created and then log.
# The current code has:
#   async with AsyncSessionLocal() as db:
#       await log_audit(db, audit_data)
# We'll change to just await log_audit(audit_data) and remove the async with.

pattern = r'async with AsyncSessionLocal\(\) as db:\n\s+await log_audit\(db, audit_data\)'
replacement = 'await log_audit(audit_data)'
new_scan = re.sub(pattern, replacement, scan_content)

# Also ensure the import of log_audit remains (no change)
write_file(scan_path, new_scan)

print("✅ Fixed DB session conflict.")
print("Now run: pytest src/tests/ -v")
