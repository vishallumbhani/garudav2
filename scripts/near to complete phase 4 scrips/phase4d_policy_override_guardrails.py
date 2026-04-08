#!/usr/bin/env python3
"""
Phase 4D: Policy overridability guardrails

Adds:
- is_overridable
- override_scope

Then marks sensitive policies as non-overridable.
"""

import os
import asyncio
import asyncpg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://garuda:change_this_local_password@localhost:5432/garuda"
)

if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")


async def patch_policy_table():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print("Connected to database")

        await conn.execute("""
            ALTER TABLE policies
            ADD COLUMN IF NOT EXISTS is_overridable BOOLEAN NOT NULL DEFAULT TRUE,
            ADD COLUMN IF NOT EXISTS override_scope VARCHAR(30) NOT NULL DEFAULT 'allow'
        """)
        print("Added overridability columns to policies")

        # Mark high-risk / global-hard-stop policies as non-overridable
        await conn.execute("""
            UPDATE policies
            SET
                is_overridable = FALSE,
                override_scope = 'none'
            WHERE policy_key IN (
                'block_private_keys',
                'block_system_prompt_exposure',
                'block_cross_tenant_access',
                'block_master_credentials',
                'block_root_secrets'
            )
        """)
        print("Updated sensitive policies to non-overridable")

        rows = await conn.fetch("""
            SELECT policy_key, action, is_overridable, override_scope
            FROM policies
            ORDER BY policy_key
        """)

        print("\nPolicy override settings:")
        for r in rows:
            print(
                f" - {r['policy_key']}: action={r['action']}, "
                f"is_overridable={r['is_overridable']}, override_scope={r['override_scope']}"
            )

        print("\nPhase 4D policy override guardrails patch completed successfully")

    finally:
        await conn.close()


async def main():
    await patch_policy_table()


if __name__ == "__main__":
    asyncio.run(main())