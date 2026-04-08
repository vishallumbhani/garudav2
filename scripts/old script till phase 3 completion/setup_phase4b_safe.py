#!/usr/bin/env python3
"""
Phase 4B: Policy engine (safe – adds policy evaluation without breaking Phase 3).
- Creates policies tables.
- Seeds example policies.
- Updates Yudhishthira to evaluate policies.
- Passes policy context from scan_service.
- Patches Krishna to use policy_action.
"""

import os
import asyncio
import asyncpg
import json
import re
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://garuda:change_this_local_password@localhost:5432/garuda")
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

async def create_policy_tables():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS policies (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                policy_key VARCHAR(100) UNIQUE NOT NULL,
                policy_name VARCHAR(200) NOT NULL,
                policy_level VARCHAR(30) NOT NULL, -- global, regulatory, tenant
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
        print("✅ Policy tables created/verified.")
    finally:
        await conn.close()

async def seed_policies():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Get default tenant id
        tenant_id = await conn.fetchval("SELECT id FROM tenants WHERE tenant_key = 'default'")
        if not tenant_id:
            print("Default tenant not found. Run Phase 4A first.")
            return

        # Global policy: block private keys
        await conn.execute("""
            INSERT INTO policies (policy_key, policy_name, policy_level, applies_to, conditions_json, action, severity)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (policy_key) DO UPDATE SET conditions_json = EXCLUDED.conditions_json
        """, "block_private_keys", "Block private keys globally", "global",
           json.dumps(["scan:text", "scan:file", "rag:output"]),
           json.dumps({"secret_type": "private_key"}), "block", "critical")

        # Regulatory policy: block PHI
        await conn.execute("""
            INSERT INTO policies (policy_key, policy_name, policy_level, applies_to, conditions_json, action, severity)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (policy_key) DO NOTHING
        """, "phi_block", "Block PHI content", "regulatory",
           json.dumps(["scan:text", "scan:file", "rag:output"]),
           json.dumps({"data_categories": ["phi"]}), "block", "high")

        # Tenant policy: challenge HIGH sensitivity (example)
        await conn.execute("""
            INSERT INTO policies (policy_key, policy_name, policy_level, tenant_id, applies_to, conditions_json, action, severity)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (policy_key) DO NOTHING
        """, "tenant_high_sensitivity", "Challenge HIGH sensitivity", "tenant", tenant_id,
           json.dumps(["scan:text", "scan:file"]),
           json.dumps({"sensitivity_label": "HIGH"}), "challenge", "medium")

        print("✅ Example policies seeded.")
    finally:
        await conn.close()

def update_yudhishthira():
    yudh_path = Path("src/engines/yudhishthira/engine.py")
    # Create a version that evaluates policies and returns policy_action, reason_codes
    yudh_content = '''"""
Yudhishthira – policy engine with hierarchy and overrides (sync version).
"""

import psycopg2
import json
from typing import Dict, Any
from src.core.config import settings

class Yudhishthira:
    def __init__(self):
        self.db_url = settings.DATABASE_URL.replace("+asyncpg", "")

    def run(self, request, bhishma_result, context: Dict[str, Any] = None) -> Dict[str, Any]:
        if context is None:
            context = {}
        tenant_key = context.get("tenant_id")
        endpoint = context.get("endpoint", "scan:text")
        data_categories = context.get("data_categories", [])
        sensitivity_label = context.get("sensitivity_label", "LOW")
        secret_severity = context.get("secret_severity")
        conn = psycopg2.connect(self.db_url)
        try:
            with conn.cursor() as cur:
                # Resolve tenant UUID
                cur.execute("SELECT id FROM tenants WHERE tenant_key = %s", (tenant_key,))
                row = cur.fetchone()
                tenant_id = row[0] if row else None
                cur.execute("""
                    SELECT p.*, po.override_action, po.override_reason
                    FROM policies p
                    LEFT JOIN policy_overrides po ON p.id = po.policy_id AND po.tenant_id = %s
                    WHERE p.enabled = true
                    AND (p.policy_level = 'global' OR (p.policy_level = 'regulatory') OR (p.policy_level = 'tenant' AND p.tenant_id = %s))
                    ORDER BY CASE p.policy_level
                        WHEN 'global' THEN 1
                        WHEN 'regulatory' THEN 2
                        WHEN 'tenant' THEN 3
                    END
                """, (tenant_id, tenant_id))
                rows = cur.fetchall()
                col_names = [desc[0] for desc in cur.description]
                action_rank = {"allow": 0, "monitor": 1, "challenge": 2, "block": 3}
                final_action = "allow"
                reason_codes = []
                matched_policies = []
                for row in rows:
                    row_dict = dict(zip(col_names, row))
                    applies_to = row_dict["applies_to"]
                    if endpoint not in applies_to:
                        continue
                    conditions = row_dict["conditions_json"]
                    match = True
                    if "secret_type" in conditions:
                        if secret_severity != conditions["secret_type"]:
                            match = False
                    if "data_categories" in conditions:
                        if not any(cat in data_categories for cat in conditions["data_categories"]):
                            match = False
                    if "sensitivity_label" in conditions:
                        if sensitivity_label != conditions["sensitivity_label"]:
                            match = False
                    if match:
                        policy_action = row_dict["override_action"] if row_dict["override_action"] else row_dict["action"]
                        if action_rank.get(policy_action, 0) > action_rank.get(final_action, 0):
                            final_action = policy_action
                        reason_codes.append(f"POLICY_{row_dict['policy_key'].upper()}")
                        matched_policies.append(row_dict["policy_key"])
                if not matched_policies:
                    final_action = "allow"
                    reason_codes.append("NO_POLICY_MATCH")
                # Modifier (optional)
                modifier_map = {"allow": 1.0, "monitor": 1.0, "challenge": 1.2, "block": 1.5}
                modifier = modifier_map.get(final_action, 1.0)
                return {
                    "engine": "yudhishthira",
                    "status": "ok",
                    "modifier": modifier,
                    "policy_action": final_action,
                    "policy_reason": f"Matched policies: {', '.join(matched_policies)}",
                    "reason_codes": reason_codes,
                    "matched_policies": matched_policies,
                }
        finally:
            conn.close()
'''
    yudh_path.write_text(yudh_content)
    print("✅ Updated Yudhishthira to evaluate policies.")

def update_scan_service_context():
    scan_path = Path("src/services/scan_service.py")
    content = scan_path.read_text()
    # Find where classification_result is obtained and add policy context building
    if "classification_result = fallback.wrap_engine" in content:
        # Insert after classification_result is added to engine_results
        marker = "engine_results[\"data_classification\"] = classification_result"
        if marker in content:
            insert_code = '''

    # Build policy context for Yudhishthira
    policy_context = {
        "tenant_id": request.tenant_id,
        "endpoint": "scan:text",
        "data_categories": classification_result.get("data_categories", []),
        "sensitivity_label": classification_result.get("sensitivity_label", "LOW"),
        "secret_severity": classification_result.get("secret_severity"),
    }
'''
            content = content.replace(marker, marker + insert_code)
            # Also modify the yudhishthira call to pass policy_context
            old_call = 'yudhishthira_result = fallback.wrap_engine("yudhishthira", Yudhishthira().run, request, bhishma_result)'
            new_call = 'yudhishthira_result = fallback.wrap_engine("yudhishthira", Yudhishthira().run, request, bhishma_result, policy_context)'
            if old_call in content:
                content = content.replace(old_call, new_call)
            else:
                print("Could not find Yudhishthira call; manual update may be needed.")
            scan_path.write_text(content)
            print("✅ Added policy context to scan_service.")
        else:
            print("Marker not found for classification_result.")
    else:
        print("Could not find classification_result in scan_service.py")

def patch_krishna_for_policy():
    krishna_path = Path("src/engines/krishna/engine.py")
    content = krishna_path.read_text()
    # Add extraction of policy_action and reason_codes from yudhishthira
    if "yudhishthira = engine_results.get(\"yudhishthira\", {})" in content:
        # Add after that line
        marker = "yudhishthira = engine_results.get(\"yudhishthira\", {}) or {}"
        if marker in content:
            insert_code = '''
        policy_action = yudhishthira.get("policy_action")
        policy_reason_codes = yudhishthira.get("reason_codes", [])
'''
            content = content.replace(marker, marker + insert_code)
        else:
            print("Could not find yudhishthira extraction.")
    else:
        print("yudhishthira extraction not found.")
    # Add policy_action to decision logic (after sensitivity floor but before secret severity)
    # Find the sensitivity floor block
    if "sensitivity_label = classification.get(\"sensitivity_label\", \"LOW\")" in content:
        # Insert after that block
        marker = "if sensitivity_label == \"CRITICAL\":"
        if marker in content:
            insert_code = '''
        # Policy override from Yudhishthira
        if policy_action == "block":
            decision = "block"
            decision_logic += f" (policy_action={policy_action} -> block)"
        elif policy_action == "challenge" and decision != "block":
            decision = "challenge"
            decision_logic += f" (policy_action={policy_action} -> challenge)"
        elif policy_action == "monitor" and decision not in ["block", "challenge"]:
            decision = "monitor"
            decision_logic += f" (policy_action={policy_action} -> monitor)"
'''
            content = content.replace(marker, insert_code + "\n        " + marker)
            print("Added policy_action to Krishna decision logic.")
        else:
            print("Could not find sensitivity floor marker.")
    else:
        print("Sensitivity floor not found.")
    # Add policy_reason_codes to trace
    trace_marker = '"decision_logic": decision_logic,'
    if trace_marker in content:
        insert_trace = '''
            "policy_action": policy_action,
            "policy_reason_codes": policy_reason_codes,
'''
        content = content.replace(trace_marker, trace_marker + "\n" + insert_trace)
        print("Added policy fields to trace.")
    else:
        print("Could not find decision_logic in trace.")
    krishna_path.write_text(content)
    print("✅ Krishna patched to use policy_action.")

async def main():
    print("Phase 4B Setup (safe – adds policy engine)")
    await create_policy_tables()
    await seed_policies()
    update_yudhishthira()
    update_scan_service_context()
    patch_krishna_for_policy()
    print("Phase 4B complete. Restart the server and test with private key prompt.")
    print("You should see policy_action and policy_reason_codes in the trace.")

if __name__ == "__main__":
    asyncio.run(main())
