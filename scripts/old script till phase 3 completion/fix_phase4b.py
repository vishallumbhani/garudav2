import os
import re
from pathlib import Path

# 1. Convert Yudhishthira to sync (use psycopg2 instead of asyncpg)
yudh_path = Path("src/engines/yudhishthira/engine.py")
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
        tenant_id = context.get("tenant_id")
        user_role = context.get("user_role", "viewer")
        endpoint = context.get("endpoint", "scan:text")
        data_categories = context.get("data_categories", [])
        sensitivity_label = context.get("sensitivity_label", "LOW")
        secret_severity = context.get("secret_severity")
        conn = psycopg2.connect(self.db_url)
        try:
            with conn.cursor() as cur:
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
print("✅ Yudhishthira converted to sync.")

# 2. Add hanuman_info extraction to Krishna
krishna_path = Path("src/engines/krishna/engine.py")
with open(krishna_path, "r") as f:
    krishna = f.read()

if "hanuman_info = engine_results.get(\"hanuman\", {})" not in krishna:
    # Insert after threat_memory extraction
    marker = "threat_memory = engine_results.get(\"threat_memory\", {})"
    if marker in krishna:
        krishna = krishna.replace(marker, marker + "\n        hanuman_info = engine_results.get(\"hanuman\", {}) or {}")
        with open(krishna_path, "w") as f:
            f.write(krishna)
        print("✅ Added hanuman_info extraction.")
    else:
        print("⚠️ Could not find insertion point for hanuman_info. Manual edit may be needed.")

# 3. Ensure external_score is integer
if "external_score = int(round(modified_score * 100))" not in krishna:
    # Add it if missing
    krishna = krishna.replace("external_score = modified_score * 100", "external_score = int(round(modified_score * 100))")
    with open(krishna_path, "w") as f:
        f.write(krishna)
    print("✅ Fixed external_score to integer.")

# 4. Install psycopg2 if needed
try:
    import psycopg2
except ImportError:
    os.system("pip install psycopg2-binary")
    print("📦 Installed psycopg2-binary.")

print("Phase 4B fixes applied. Restart the server and test.")
