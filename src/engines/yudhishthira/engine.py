"""
Yudhishthira - policy engine with hierarchy, overrides, and overridability metadata.
"""

import psycopg2
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
                # Resolve tenant UUID from tenant_key
                cur.execute("SELECT id FROM tenants WHERE tenant_key = %s", (tenant_key,))
                row = cur.fetchone()
                tenant_id = row[0] if row else None

                cur.execute("""
                    SELECT p.*, po.override_action, po.override_reason
                    FROM policies p
                    LEFT JOIN policy_overrides po
                      ON p.id = po.policy_id AND po.tenant_id = %s
                    WHERE p.enabled = true
                      AND (
                        p.policy_level = 'global'
                        OR p.policy_level = 'regulatory'
                        OR (p.policy_level = 'tenant' AND p.tenant_id = %s)
                      )
                    ORDER BY CASE p.policy_level
                        WHEN 'global' THEN 1
                        WHEN 'regulatory' THEN 2
                        WHEN 'tenant' THEN 3
                        ELSE 99
                    END
                """, (tenant_id, tenant_id))

                rows = cur.fetchall()
                col_names = [desc[0] for desc in cur.description]

                action_rank = {"allow": 0, "monitor": 1, "challenge": 2, "block": 3}
                final_action = "allow"
                reason_codes = []
                matched_policies = []
                matched_policy_meta = []
                global_guardrail_hit = False
                match_debug = []

                supported_keys = {
                    "secret_type",
                    "secret_severity",
                    "data_categories",
                    "sensitivity_label",
                }

                for row in rows:
                    row_dict = dict(zip(col_names, row))

                    applies_to = row_dict.get("applies_to") or []
                    if endpoint not in applies_to:
                        continue

                    conditions = row_dict.get("conditions_json") or {}
                    match = True
                    reasons = []

                    # Reject unknown condition keys
                    unknown_keys = set(conditions.keys()) - supported_keys
                    if unknown_keys:
                        match = False
                        reasons.append(f"unknown_condition_keys:{sorted(list(unknown_keys))}")

                    # secret_type
                    if match and "secret_type" in conditions:
                        if secret_severity != conditions["secret_type"]:
                            match = False
                            reasons.append(
                                f"secret_type_mismatch(expected={conditions['secret_type']}, actual={secret_severity})"
                            )

                    # secret_severity
                    if match and "secret_severity" in conditions:
                        if secret_severity != conditions["secret_severity"]:
                            match = False
                            reasons.append(
                                f"secret_severity_mismatch(expected={conditions['secret_severity']}, actual={secret_severity})"
                            )

                    # data_categories
                    if match and "data_categories" in conditions:
                        if not any(cat in data_categories for cat in conditions["data_categories"]):
                            match = False
                            reasons.append(
                                f"data_categories_no_overlap(expected={conditions['data_categories']}, actual={data_categories})"
                            )

                    # sensitivity_label
                    if match and "sensitivity_label" in conditions:
                        if sensitivity_label != conditions["sensitivity_label"]:
                            match = False
                            reasons.append(
                                f"sensitivity_label_mismatch(expected={conditions['sensitivity_label']}, actual={sensitivity_label})"
                            )

                    match_debug.append({
                        "policy_key": row_dict.get("policy_key"),
                        "conditions": conditions,
                        "match": match,
                        "reasons": reasons,
                        "secret_severity": secret_severity,
                        "data_categories": data_categories,
                        "sensitivity_label": sensitivity_label,
                    })

                    if not match:
                        continue

                    policy_action = row_dict["override_action"] if row_dict.get("override_action") else row_dict["action"]
                    policy_key = row_dict["policy_key"]
                    policy_level = row_dict.get("policy_level", "tenant")
                    is_overridable = row_dict.get("is_overridable", True)
                    override_scope = row_dict.get("override_scope", "allow") or "allow"

                    if action_rank.get(policy_action, 0) > action_rank.get(final_action, 0):
                        final_action = policy_action

                    code = f"POLICY_{policy_key.upper()}"
                    reason_codes.append(code)
                    matched_policies.append(policy_key)

                    meta = {
                        "policy_key": policy_key,
                        "action": policy_action,
                        "policy_level": policy_level,
                        "is_overridable": bool(is_overridable),
                        "override_scope": override_scope,
                    }
                    matched_policy_meta.append(meta)

                    if policy_level == "global" and policy_action == "block":
                        global_guardrail_hit = True

                if not matched_policies:
                    final_action = "allow"

                if matched_policy_meta:
                    if any(not p["is_overridable"] or p["override_scope"] == "none" for p in matched_policy_meta):
                        effective_override_scope = "none"
                    elif any(p["override_scope"] == "challenge_only" for p in matched_policy_meta):
                        effective_override_scope = "challenge_only"
                    else:
                        effective_override_scope = "allow"
                else:
                    effective_override_scope = "allow"

                non_overridable_match = any(
                    (not p["is_overridable"]) or p["override_scope"] == "none"
                    for p in matched_policy_meta
                )

                modifier_map = {
                    "allow": 1.0,
                    "monitor": 1.0,
                    "challenge": 1.2,
                    "block": 1.5,
                }
                modifier = modifier_map.get(final_action, 1.0)

                return {
                    "engine": "yudhishthira",
                    "status": "ok",
                    "modifier": modifier,
                    "policy_action": final_action,
                    "policy_reason": f"Matched policies: {', '.join(matched_policies)}" if matched_policies else "No policy match",
                    "reason_codes": reason_codes,
                    "matched_policies": matched_policies,
                    "matched_policy_meta": matched_policy_meta,
                    "non_overridable_match": non_overridable_match,
                    "effective_override_scope": effective_override_scope,
                    "global_guardrail_hit": global_guardrail_hit,
                    "match_debug": match_debug,
                }
        finally:
            conn.close()