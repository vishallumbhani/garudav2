#!/usr/bin/env python3
"""
Phase 4 Audit Schema Update Script

Adds missing governance fields to audit_logs table:
- endpoint
- policy_action
- policy_reason_codes
- override_applied
"""

import os
import asyncio
import asyncpg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://garuda:change_this_local_password@localhost:5432/garuda"
)

# Fix for asyncpg format if needed
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")


async def update_audit_schema():
    print("Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        print("Updating audit_logs schema...")

        await conn.execute("""
            ALTER TABLE audit_logs
            ADD COLUMN IF NOT EXISTS endpoint VARCHAR(50),
            ADD COLUMN IF NOT EXISTS policy_action VARCHAR(50),
            ADD COLUMN IF NOT EXISTS policy_reason_codes JSONB,
            ADD COLUMN IF NOT EXISTS override_applied BOOLEAN DEFAULT FALSE;
        """)

        print("? audit_logs schema updated successfully.")

        # Optional verification
        columns = await conn.fetch("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'audit_logs'
        """)

        print("\nCurrent columns in audit_logs:")
        for col in columns:
            print(f" - {col['column_name']}")

    except Exception as e:
        print("? Error updating schema:", str(e))
    finally:
        await conn.close()
        print("Database connection closed.")


if __name__ == "__main__":
    asyncio.run(update_audit_schema())