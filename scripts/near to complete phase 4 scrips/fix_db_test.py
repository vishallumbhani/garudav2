#!/usr/bin/env python3
"""
Fix DB storage test to use raw asyncpg connection.
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

# Update test_api.py with a working DB test using raw asyncpg
with open("src/tests/test_api.py", "r") as f:
    test_content = f.read()

new_db_test = '''@pytest.mark.asyncio
async def test_db_storage():
    """Test that audit logs are correctly stored in PostgreSQL using raw asyncpg."""
    import asyncpg
    from src.core.config import settings

    # Extract database URL components
    # Format: postgresql+asyncpg://user:pass@host:port/dbname
    db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    # Connect directly
    conn = await asyncpg.connect(db_url)
    try:
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

        # Now query directly
        row = await conn.fetchrow(
            "SELECT * FROM audit_logs WHERE event_id = $1",
            event_id
        )
        assert row is not None, f"No audit log found for event_id {event_id}"
        # Verify required fields exist
        assert row["event_id"] == event_id
        assert row["decision"] is not None
        # The trace is in engine_results (JSON)
        engine_results = row["engine_results"]
        assert "krishna" in engine_results
        krishna = engine_results["krishna"]
        assert "details" in krishna
        trace = krishna["details"]["trace"]
        assert "trace_version" in trace
        assert "status" in trace
        assert "confidence" in trace
    finally:
        await conn.close()
'''

# Replace the old test_db_storage function
import re
pattern = r'@pytest\.mark\.asyncio\s+async def test_db_storage\(\):.*?(?=\n\ndef |\Z)'
test_content = re.sub(pattern, new_db_test, test_content, flags=re.DOTALL)

write_file("src/tests/test_api.py", test_content)

print("✅ DB test rewritten to use raw asyncpg.")
print("Now install asyncpg if not already (it is in requirements).")
print("Run: pytest src/tests/ -v")
