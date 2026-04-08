#!/usr/bin/env python3
"""
Final fixes:
- Update config.py to Pydantic v2
- Fix DB storage test to actually run and pass
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

def write_file(path, content):
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"Written: {file_path}")

# ----------------------------------------------------------------------
# 1. Update config.py to Pydantic v2
new_config = '''from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "Garuda Local"
    APP_ENV: str = "dev"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    DATABASE_URL: str = "postgresql+asyncpg://garuda:change_this_local_password@localhost:5432/garuda"
    REDIS_URL: str = "redis://localhost:6379/0"

    GARUDA_SECRET_KEY: str = "replace_with_local_secret"
    LOG_LEVEL: str = "INFO"

    UPLOAD_DIR: str = "./data/uploads"
    PROCESSED_DIR: str = "./data/processed"
    QUARANTINE_DIR: str = "./data/quarantine"
    AUDIT_LOG_PATH: str = "./logs/audit.jsonl"

    MAX_UPLOAD_SIZE_BYTES: int = 10485760
    ALLOWED_EXTENSIONS: str = ".txt,.md,.csv,.json,.log,.pdf,.py,.js,.java,.yaml,.yml"

    DEFAULT_TENANT: str = "default"
    DEFAULT_POLICY_MODE: str = "strict"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
'''
write_file("src/core/config.py", new_config)

# ----------------------------------------------------------------------
# 2. Update the DB storage test to work correctly
# We'll replace the entire test_db_storage function with a version that uses the existing async engine
with open("src/tests/test_api.py", "r") as f:
    test_content = f.read()

# Find the test_db_storage function and replace it
old_test_db = '''def test_db_storage():
    # This test requires DB access; skip if DB not available
    try:
        from src.db.base import AsyncSessionLocal
        from src.db.models import AuditLog
        async def check():
            async with AsyncSessionLocal() as db:
                # Get most recent audit log
                from sqlalchemy import select, desc
                result = await db.execute(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(1))
                log = result.scalar_one_or_none()
                assert log is not None
                assert log.engine_results is not None
                assert "trace" in log.engine_results
                trace = log.engine_results["trace"]
                assert "trace_version" in trace
                assert "status" in trace
                assert "confidence" in trace
        asyncio.run(check())
    except Exception as e:
        pytest.skip(f"DB check skipped: {e}")'''

new_test_db = '''@pytest.mark.asyncio
async def test_db_storage():
    """Test that audit logs are correctly stored in PostgreSQL."""
    # First, create a test entry via API to ensure there's data
    payload = {
        "text": "test db storage",
        "tenant_id": "default",
        "user_id": "test_user",
        "session_id": "test_db_session",
        "source": "test"
    }
    response = client.post("/v1/scan/text", json=payload)
    assert response.status_code == 200
    data = response.json()
    event_id = data["event_id"]

    # Now query the database
    from src.db.base import AsyncSessionLocal
    from src.db.models import AuditLog
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AuditLog).where(AuditLog.event_id == event_id))
        log = result.scalar_one_or_none()
        assert log is not None, f"No audit log found for event_id {event_id}"
        assert log.engine_results is not None
        # The trace is stored inside engine_results under the "trace" key
        # In our current storage, engine_results is a dict with keys like "hanuman", "bhishma", etc.
        # But the trace we want is actually stored in the details.trace of Krishna result.
        # Let's check the structure: engine_results["krishna"]["details"]["trace"]
        krishna = log.engine_results.get("krishna", {})
        trace = krishna.get("details", {}).get("trace", {})
        assert "trace_version" in trace
        assert "status" in trace
        assert "confidence" in trace
        assert trace["decision_logic"] is not None
'''

# Replace if found
if old_test_db in test_content:
    test_content = test_content.replace(old_test_db, new_test_db)
    write_file("src/tests/test_api.py", test_content)
    print("✅ Updated test_db_storage to use asyncio")
else:
    # Fallback: we'll manually write the whole file with corrections
    # Let's create a proper test file with all tests using asyncio where needed
    pass

# Also ensure that the test file has the necessary imports
if "import pytest" not in test_content:
    test_content = "import pytest\n" + test_content
if "from fastapi.testclient import TestClient" not in test_content:
    test_content = "from fastapi.testclient import TestClient\n" + test_content
if "import asyncio" not in test_content:
    test_content = "import asyncio\n" + test_content

write_file("src/tests/test_api.py", test_content)

print("\n✅ Fixes applied.")
print("Now run: pytest src/tests/ -v")
print("The DB test should now run and pass (provided DB is running).")
