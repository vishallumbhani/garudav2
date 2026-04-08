#!/usr/bin/env python3
"""
Fix indentation in Krishna engine after adding Shakuni.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

# Write a clean Krishna engine with correct indentation
krishna_content = '''"""
Decision aggregator with weighted scoring, policy modifier, behavior escalation, and Shakuni.
"""

from typing import Dict, Any

class Krishna:
    def __init__(self):
        self.weights = {"bhishma": 0.6, "hanuman": 0.25, "shakuni": 0.15}
        self.trace_version = "1.1"

    def run(self, request, engine_results: Dict[str, Any]) -> Dict[str, Any]:
        bhishma = engine_results.get("bhishma", {})
        hanuman = engine_results.get("hanuman", {})
        shakuni = engine_results.get("shakuni", {})
        yudhishthira = engine_results.get("yudhishthira", {})
        behavior = engine_results.get("behavior", {})

        bhishma_score = bhishma.get("score", 0.5)
        hanuman_score = hanuman.get("score", 0.5)
        shakuni_score = shakuni.get("score", 0.5)

        base_weighted = (self.weights["bhishma"] * bhishma_score +
                         self.weights["hanuman"] * hanuman_score +
                         self.weights["shakuni"] * shakuni_score)

        policy_modifier = yudhishthira.get("modifier", 1.0)
        behavior_modifier = behavior.get("escalation_factor", 1.0)
        behavior_reason = behavior.get("escalation_reason", "no data")

        modified_score = base_weighted * policy_modifier * behavior_modifier
        modified_score = min(modified_score, 0.95)

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

        # Determine overall status
        if any(r.get("status") == "degraded" for r in engine_results.values()):
            status = "degraded"
        else:
            status = "ok"

        # Compute overall confidence
        bhishma_conf = bhishma.get("confidence", 0.7)
        hanuman_conf = hanuman.get("confidence", 0.8)
        shakuni_conf = shakuni.get("confidence", 0.8)
        confidence = (bhishma_conf * 0.5 + hanuman_conf * 0.3 + shakuni_conf * 0.2) * (1 / max(1.0, policy_modifier)) * (1 / max(1.0, behavior_modifier))
        confidence = round(min(confidence, 0.95), 3)

        trace = {
            "trace_version": self.trace_version,
            "status": status,
            "confidence": confidence,
            "weights": self.weights,
            "scores": {
                "bhishma": round(bhishma_score, 3),
                "hanuman": round(hanuman_score, 3),
                "shakuni": round(shakuni_score, 3)
            },
            "base_weighted_score": round(base_weighted, 3),
            "policy_modifier": round(policy_modifier, 2),
            "behavior_modifier": round(behavior_modifier, 2),
            "behavior_reason": behavior_reason,
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
'''
with open("src/engines/krishna/engine.py", "w") as f:
    f.write(krishna_content)

print("✅ Krishna engine rewritten with proper indentation.")
print("Now restart the server.")
