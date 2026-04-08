#!/usr/bin/env python3
"""
Phase 4C: Audit schema maturity patch
- Adds missing audit columns required by Phase 4
- Backfills policy fields from trace JSON where possible
- Safe/idempotent
"""

import os
import asyncio
import asyncpg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://garuda:change_this_local_password@localhost:5432/garuda",
)

if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")


async def patch_audit_table():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print("Connected to database")

        await conn.execute("""
            ALTER TABLE audit_logs
            ADD COLUMN IF NOT EXISTS endpoint TEXT,
            ADD COLUMN IF NOT EXISTS policy_action TEXT,
            ADD COLUMN IF NOT EXISTS policy_reason_codes JSONB,
            ADD COLUMN IF NOT EXISTS override_applied BOOLEAN NOT NULL DEFAULT FALSE
        """)
        print("Added missing audit columns")

        await conn.execute("""
            UPDATE audit_logs
            SET
                endpoint = COALESCE(endpoint, trace->>'endpoint'),
                policy_action = COALESCE(policy_action, trace->>'policy_action'),
                policy_reason_codes = COALESCE(
                    policy_reason_codes,
                    CASE
                        WHEN jsonb_typeof(trace::jsonb -> 'policy_reason_codes') = 'array'
                        THEN trace::jsonb -> 'policy_reason_codes'
                        ELSE '[]'::jsonb
                    END
                ),
                override_applied = COALESCE(
                    override_applied,
                    CASE
                        WHEN trace::jsonb ? 'override' THEN TRUE
                        ELSE FALSE
                    END
                )
            WHERE
                endpoint IS NULL
                OR policy_action IS NULL
                OR policy_reason_codes IS NULL
        """)
        print("Backfilled existing audit rows from trace where possible")

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant_created_at
            ON audit_logs (tenant_id, created_at DESC)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_decision_created_at
            ON audit_logs (decision, created_at DESC)
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_policy_action
            ON audit_logs (policy_action)
        """)

        print("Created helpful indexes")
        print("Phase 4C audit patch completed successfully")

    finally:
        await conn.close()


async def main():
    await patch_audit_table()


if __name__ == "__main__":
    asyncio.run(main())
