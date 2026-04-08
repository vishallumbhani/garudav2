#!/usr/bin/env python3
"""
Final trace improvements:
- Add base_weighted_score, modified_score, override_reason.
- Flush Redis before each test (optional).
- Ensure Yudhishthira provides override_reason.
"""

import os
import redis
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

def write_file(path, content):
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"Written: {file_path}")

# ----------------------------------------------------------------------
# 1. Update Yudhishthira to include override_reason
write_file("src/engines/yudhishthira/engine.py", '''\
"""
Policy/tenant engine – outputs policy flags and modifiers.
"""

from typing import Dict, Any

class Yudhishthira:
    def __init__(self):
        self.tenant_policies = {
            "default": {"mode": "strict", "block_threshold": 0.7},
            "test": {"mode": "permissive", "block_threshold": 0.9},
        }

    def run(self, request, bhishma_result) -> Dict[str, Any]:
        tenant = request.tenant_id
        policy = self.tenant_policies.get(tenant, self.tenant_policies["default"])
        mode = policy["mode"]

        modifier = 1.0
        override_action = None
        override_reason = None
        labels = []
        reason = "No policy override."

        critical_matches = [m for m in bhishma_result.get("matched_patterns", []) if m.get("type") == "critical"]
        if critical_matches:
            if mode == "strict":
                override_action = "block"
                override_reason = "Critical pattern matched under strict policy"
                labels.append("critical_pattern_block")
                reason = "Critical pattern matched: forced block."
            else:
                labels.append("critical_pattern_warning")
                reason = "Critical pattern matched (permissive mode)."
            modifier = 1.5

        sensitive_matches = [m for m in bhishma_result.get("matched_patterns", []) if m.get("type") == "sensitive"]
        if sensitive_matches:
            if mode == "strict":
                modifier = max(modifier, 1.2)
                labels.append("strict_mode_sensitive")
                reason = "Strict mode: sensitive data escalates risk."
            else:
                labels.append("sensitive_data_warning")

        return {
            "engine": "yudhishthira",
            "status": "ok",
            "modifier": round(modifier, 2),
            "override_action": override_action,
            "override_reason": override_reason,
            "labels": labels,
            "reason": reason
        }
''')

# ----------------------------------------------------------------------
# 2. Update Krishna with improved trace
write_file("src/engines/krishna/engine.py", '''\
"""
Decision aggregator with improved trace.
"""

from typing import Dict, Any

class Krishna:
    def __init__(self):
        self.weights = {"bhishma": 0.7, "hanuman": 0.3}

    def run(self, request, engine_results: Dict[str, Any]) -> Dict[str, Any]:
        bhishma = engine_results.get("bhishma", {})
        hanuman = engine_results.get("hanuman", {})
        yudhishthira = engine_results.get("yudhishthira", {})
        behavior = engine_results.get("behavior", {})

        bhishma_score = bhishma.get("score", 0.5)
        hanuman_score = hanuman.get("score", 0.5)

        # Weighted base score
        base_weighted = (self.weights["bhishma"] * bhishma_score +
                         self.weights["hanuman"] * hanuman_score)

        # Apply policy modifier
        policy_modifier = yudhishthira.get("modifier", 1.0)
        # Apply behavior modifier
        behavior_modifier = behavior.get("escalation_factor", 1.0)

        modified_score = base_weighted * policy_modifier * behavior_modifier
        modified_score = min(modified_score, 0.95)

        # Check for policy override
        override_action = yudhishthira.get("override_action")
        override_reason = yudhishthira.get("override_reason")

        if override_action:
            decision = override_action
            decision_logic = f"override={override_action}"
        else:
            if modified_score >= 0.8:
                decision = "block"
            elif modified_score >= 0.6:
                decision = "challenge"
            elif modified_score >= 0.3:
                decision = "monitor"
            else:
                decision = "allow"
            decision_logic = f"score={modified_score:.3f} -> {decision}"

        # Build trace
        trace = {
            "weights": self.weights,
            "scores": {
                "bhishma": round(bhishma_score, 3),
                "hanuman": round(hanuman_score, 3)
            },
            "base_weighted_score": round(base_weighted, 3),
            "policy_modifier": round(policy_modifier, 2),
            "behavior_modifier": round(behavior_modifier, 2),
            "modified_score": round(modified_score, 3),
            "decision_logic": decision_logic
        }
        if override_action:
            trace["override"] = override_action
            trace["override_reason"] = override_reason

        external_score = int(round(modified_score * 100))

        return {
            "engine": "krishna",
            "score": external_score,
            "normalized_score": round(modified_score, 3),
            "decision": decision,
            "details": {"trace": trace}
        }
''')

# ----------------------------------------------------------------------
# 3. Optional: Add Redis flush to test script (not included here)
print("✅ Trace improvements applied.")
print("Now run: redis-cli FLUSHALL")
print("Then restart the server and run ./scripts/test_api.sh")
