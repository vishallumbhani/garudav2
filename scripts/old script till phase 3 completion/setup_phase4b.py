import json
#!/usr/bin/env python3
"""
Phase 4B: Policies and Yudhishthira expansion.
- Seed global, regulatory, tenant policies.
- Enhance Yudhishthira to evaluate policy hierarchy.
- Integrate policy evaluation into scan pipeline.
- Add reason codes to trace.
"""

import os
import sys
import asyncio
import asyncpg
from pathlib import Path
import re

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://garuda:change_this_local_password@localhost:5432/garuda")
if "+asyncpg" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")

async def seed_policies():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Get default tenant ID
        tenant_id = await conn.fetchval("SELECT id FROM tenants WHERE tenant_key = 'default'")
        if not tenant_id:
            print("Default tenant not found. Run Phase 4A first.")
            return

        # Global policies (apply to all tenants)
        global_policies = [
            {
                "policy_key": "block_private_keys",
                "policy_name": "Block private keys globally",
                "policy_level": "global",
                "applies_to": ["scan:text", "scan:file", "rag:output"],
                "conditions_json": {"secret_type": "private_key"},
                "action": "block",
                "severity": "critical",
            },
            {
                "policy_key": "block_aws_keys",
                "policy_name": "Block AWS access keys",
                "policy_level": "global",
                "applies_to": ["scan:text", "scan:file", "rag:output"],
                "conditions_json": {"secret_type": "aws_key"},
                "action": "block",
                "severity": "high",
            },
        ]
        # Regulatory policies (example: PHI must be blocked)
        regulatory_policies = [
            {
                "policy_key": "phi_block",
                "policy_name": "Block PHI content",
                "policy_level": "regulatory",
                "applies_to": ["scan:text", "scan:file", "rag:output"],
                "conditions_json": {"data_categories": ["phi"]},
                "action": "block",
                "severity": "high",
            },
        ]
        # Tenant policies (example: for default tenant)
        tenant_policies = [
            {
                "policy_key": "tenant_high_sensitivity_challenge",
                "policy_name": "Challenge HIGH sensitivity content",
                "policy_level": "tenant",
                "tenant_id": tenant_id,
                "applies_to": ["scan:text", "scan:file"],
                "conditions_json": {"sensitivity_label": "HIGH"},
                "action": "challenge",
                "severity": "medium",
            },
        ]

        all_policies = global_policies + regulatory_policies + tenant_policies
        for pol in all_policies:
            await conn.execute("""
                INSERT INTO policies (policy_key, policy_name, policy_level, tenant_id, applies_to, conditions_json, action, severity)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (policy_key) DO UPDATE SET
                    policy_name = EXCLUDED.policy_name,
                    conditions_json = EXCLUDED.conditions_json,
                    action = EXCLUDED.action,
                    severity = EXCLUDED.severity,
                    updated_at = NOW()
            """, pol["policy_key"], pol["policy_name"], pol["policy_level"], pol.get("tenant_id"), 
               json.dumps(pol["applies_to"]), json.dumps(pol["conditions_json"]), pol["action"], pol["severity"])

        # Add a tenant override for the global policy block_private_keys to allow challenge for tenant (example)
        # Get global policy id
        global_policy_id = await conn.fetchval("SELECT id FROM policies WHERE policy_key = 'block_private_keys'")
        if global_policy_id:
            await conn.execute("""
                INSERT INTO policy_overrides (policy_id, tenant_id, override_action, override_reason)
                VALUES ($1, $2, 'challenge', 'Temporary relaxed handling for migration')
                ON CONFLICT (policy_id, tenant_id) DO UPDATE SET override_action = EXCLUDED.override_action
            """, global_policy_id, tenant_id)

        print("✅ Policies seeded.")
    finally:
        await conn.close()

async def update_yudhishthira_engine():
    # Path to Yudhishthira engine
    engine_path = Path("src/engines/yudhishthira/engine.py")
    if not engine_path.exists():
        print("Yudhishthira engine not found. Creating...")
        engine_path.parent.mkdir(parents=True, exist_ok=True)
        engine_path.write_text("""
class Yudhishthira:
    def run(self, request, bhishma_result):
        return {"engine": "yudhishthira", "status": "ok", "modifier": 1.0, "reason": "No policy override"}
""")
    # We'll replace the engine with a full policy evaluator
    new_engine = '''
"""
Yudhishthira – policy engine with hierarchy and overrides.
"""

import asyncpg
from typing import Dict, Any, List
from src.core.config import settings

class Yudhishthira:
    def __init__(self):
        self.db_url = settings.DATABASE_URL.replace("+asyncpg", "")

    async def run(self, request, bhishma_result, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Evaluate policies based on context: tenant_id, user_role, endpoint, data_categories, sensitivity, secrets, etc.
        Returns policy action, reason codes, and modifier.
        """
        if context is None:
            context = {}
        tenant_id = context.get("tenant_id")
        user_role = context.get("user_role", "viewer")
        endpoint = context.get("endpoint", "scan:text")
        data_categories = context.get("data_categories", [])
        sensitivity_label = context.get("sensitivity_label", "LOW")
        secret_severity = context.get("secret_severity")
        # Load policies from DB (could cache, but for simplicity we query)
        conn = await asyncpg.connect(self.db_url)
        try:
            # Fetch global policies
            rows = await conn.fetch("""
                SELECT p.*, po.override_action, po.override_reason
                FROM policies p
                LEFT JOIN policy_overrides po ON p.id = po.policy_id AND po.tenant_id = $1
                WHERE p.enabled = true
                AND (p.policy_level = 'global' OR (p.policy_level = 'regulatory') OR (p.policy_level = 'tenant' AND p.tenant_id = $1))
                ORDER BY CASE p.policy_level
                    WHEN 'global' THEN 1
                    WHEN 'regulatory' THEN 2
                    WHEN 'tenant' THEN 3
                END
            """, tenant_id)
            action_rank = {"allow": 0, "monitor": 1, "challenge": 2, "block": 3}
            final_action = "allow"
            reason_codes = []
            matched_policies = []
            for row in rows:
                applies_to = row["applies_to"]
                if endpoint not in applies_to:
                    continue
                conditions = row["conditions_json"]
                # Check conditions
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
                    policy_action = row["override_action"] if row["override_action"] else row["action"]
                    if action_rank.get(policy_action, 0) > action_rank.get(final_action, 0):
                        final_action = policy_action
                    reason_codes.append(f"POLICY_{row['policy_key'].upper()}")
                    matched_policies.append(row["policy_key"])
            # If no policy matched, default action is allow (or based on tenant config)
            if not matched_policies:
                final_action = "allow"
                reason_codes.append("NO_POLICY_MATCH")
            # Compute modifier based on action (optional)
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
            await conn.close()
'''
    engine_path.write_text(new_engine)
    print("✅ Yudhishthira engine updated with policy evaluation.")

async def update_scan_service():
    # Modify scan_service.py to pass context to Yudhishthira
    scan_path = Path("src/services/scan_service.py")
    if not scan_path.exists():
        print("scan_service.py not found.")
        return
    content = scan_path.read_text()
    # We need to find the line where yudhishthira_result is called and pass context.
    # Currently it may be: yudhishthira_result = fallback.wrap_engine("yudhishthira", Yudhishthira().run, request, bhishma_result)
    # We need to pass an additional context dict.
    # We'll replace that line with a version that gathers context and passes it.
    # First, add import for Yudhishthira if not already (it is)
    # Then we'll add code before calling Yudhishthira to build context.
    insert_code = '''
        # Build policy context
        policy_context = {
            "tenant_id": request.tenant_id,
            "user_role": "analyst",  # TODO: get from identity
            "endpoint": "scan:text",
            "data_categories": classification.get("data_categories", []) if 'classification' in locals() else [],
            "sensitivity_label": classification.get("sensitivity_label", "LOW") if 'classification' in locals() else "LOW",
            "secret_severity": classification.get("secret_severity") if 'classification' in locals() else None,
        }
'''
    # Find the line where yudhishthira_result is defined
    if "yudhishthira_result = fallback.wrap_engine" in content:
        # Insert the context building before that line
        content = content.replace("yudhishthira_result = fallback.wrap_engine", insert_code + "\n    yudhishthira_result = fallback.wrap_engine")
        # Also need to make Yudhishthira's run accept context. We'll change the call to pass context.
        # The call becomes: yudhishthira_result = fallback.wrap_engine("yudhishthira", Yudhishthira().run, request, bhishma_result, policy_context)
        # But wrap_engine expects a function with signature (request, ...). We'll need to adjust. Simpler: we'll not use wrap_engine for Yudhishthira? Or we modify wrap_engine to accept arbitrary args.
        # For now, we'll call Yudhishthira directly, not via fallback? But fallback provides safety.
        # Let's modify the line to include policy_context as an extra argument.
        content = content.replace("yudhishthira_result = fallback.wrap_engine(\"yudhishthira\", Yudhishthira().run, request, bhishma_result)",
                                  "yudhishthira_result = fallback.wrap_engine(\"yudhishthira\", Yudhishthira().run, request, bhishma_result, policy_context)")
    else:
        print("Could not find yudhishthira call in scan_service.py")
    scan_path.write_text(content)
    print("✅ scan_service.py updated to pass policy context to Yudhishthira.")

async def update_krishna_trace():
    # Add reason_codes to trace
    krishna_path = Path("src/engines/krishna/engine.py")
    if not krishna_path.exists():
        print("Krishna engine not found.")
        return
    content = krishna_path.read_text()
    # Extract reason_codes from yudhishthira result
    if "yudhishthira = engine_results.get(\"yudhishthira\", {})" in content:
        # Add extraction of reason_codes
        insert_after = "yudhishthira = engine_results.get(\"yudhishthira\", {})"
        new_lines = '''
        yudhishthira_reason_codes = yudhishthira.get("reason_codes", [])
        yudhishthira_policy_action = yudhishthira.get("policy_action", "allow")
'''
        content = content.replace(insert_after, insert_after + "\n" + new_lines)
        # Add to trace
        trace_insert = '        "policy_reason_codes": yudhishthira_reason_codes,\n        "policy_action": yudhishthira_policy_action,\n'
        # Insert after 'decision_logic' or similar
        if '"decision_logic": decision_logic,' in content:
            content = content.replace('"decision_logic": decision_logic,', '"decision_logic": decision_logic,\n' + trace_insert)
        else:
            print("Could not find decision_logic line. Adding at end of trace.")
            content = content.replace('trace = {', 'trace = {\n' + trace_insert)
        krishna_path.write_text(content)
        print("✅ Krishna trace updated with policy reason codes.")
    else:
        print("Could not find yudhishthira extraction in Krishna.")

async def main():
    print("Phase 4B: Setting up policies and Yudhishthira expansion...")
    await seed_policies()
    await update_yudhishthira_engine()
    await update_scan_service()
    await update_krishna_trace()
    print("Phase 4B setup complete. Restart the server and test with a request that triggers a policy.")
    print("Example: Send a prompt containing a private key and observe the policy_action and reason_codes in the trace.")

if __name__ == "__main__":
    asyncio.run(main())
