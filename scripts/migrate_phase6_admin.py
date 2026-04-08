#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 6 Admin Tables Migration (UUID version)
Run: python scripts/migrate_phase6_admin_fixed.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.db.base import AsyncSessionLocal

# Use a fixed UUID for default tenant
DEFAULT_TENANT_UUID = "11111111-1111-1111-1111-111111111111"

async def table_exists(table_name: str) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = :table_name
            )
        """), {"table_name": table_name})
        return result.scalar()

async def create_rules_table():
    print("Creating rules table...")
    async with AsyncSessionLocal() as session:
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS rules (
                id SERIAL PRIMARY KEY,
                engine VARCHAR(50) NOT NULL,
                name VARCHAR(255) NOT NULL,
                conditions JSONB NOT NULL,
                action VARCHAR(50) NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                priority INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await session.commit()
    print("? rules table ready")

async def create_tenant_configs_table():
    print("Creating tenant_configs table...")
    async with AsyncSessionLocal() as session:
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS tenant_configs (
                tenant_id UUID PRIMARY KEY,
                strict_mode BOOLEAN DEFAULT FALSE,
                thresholds JSONB DEFAULT '{}'::jsonb,
                feature_toggles JSONB DEFAULT '{}'::jsonb,
                overrides_summary JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await session.commit()
    print("? tenant_configs table ready")

async def create_api_keys_table():
    print("Creating api_keys table...")
    async with AsyncSessionLocal() as session:
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id SERIAL PRIMARY KEY,
                key_prefix VARCHAR(16) NOT NULL UNIQUE,
                hashed_key VARCHAR(255) NOT NULL,
                tenant_id UUID NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                last_used TIMESTAMP,
                expires_at TIMESTAMP,
                enabled BOOLEAN DEFAULT TRUE
            )
        """))
        await session.commit()
    print("? api_keys table ready")

async def insert_default_tenant_config():
    async with AsyncSessionLocal() as session:
        # Check if exists
        result = await session.execute(text(
            "SELECT tenant_id FROM tenant_configs WHERE tenant_id = :tid"
        ), {"tid": DEFAULT_TENANT_UUID})
        if result.fetchone():
            print("Default tenant config already exists.")
            return
        # Insert default
        await session.execute(text("""
            INSERT INTO tenant_configs (tenant_id, strict_mode, thresholds, feature_toggles)
            VALUES (:tid, false, '{"block_threshold": 0.8, "challenge_threshold": 0.6}', '{"escalation_enabled": true, "memory_enabled": true}')
        """), {"tid": DEFAULT_TENANT_UUID})
        await session.commit()
        print(f"? Inserted default tenant config for UUID: {DEFAULT_TENANT_UUID}")

async def insert_sample_rule():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM rules"))
        count = result.scalar()
        if count > 0:
            print("Rules already exist, skipping sample.")
            return
        await session.execute(text("""
            INSERT INTO rules (engine, name, conditions, action, enabled, priority)
            VALUES (
                'bhishma',
                'Sample High Risk Rule',
                '{"score_threshold": 0.7}',
                'challenge',
                true,
                10
            )
        """))
        await session.commit()
        print("? Inserted sample rule.")

async def drop_old_tables():
    """Drop old tables if they exist with wrong schema."""
    async with AsyncSessionLocal() as session:
        # Check if tenant_configs exists and has wrong column type
        result = await session.execute(text("""
            SELECT data_type FROM information_schema.columns
            WHERE table_name = 'tenant_configs' AND column_name = 'tenant_id'
        """))
        row = result.fetchone()
        if row and row[0] != 'uuid':
            print("Dropping old tenant_configs table (wrong type)...")
            await session.execute(text("DROP TABLE IF EXISTS tenant_configs CASCADE"))
            print("Dropping old api_keys table...")
            await session.execute(text("DROP TABLE IF EXISTS api_keys CASCADE"))
            await session.commit()

async def main():
    print("=== Phase 6 Admin Tables Migration (UUID) ===")
    await drop_old_tables()
    await create_rules_table()
    await create_tenant_configs_table()
    await create_api_keys_table()
    await insert_default_tenant_config()
    await insert_sample_rule()
    print("\nMigration complete. Tables are ready for Phase 6 admin features.")

if __name__ == "__main__":
    asyncio.run(main())