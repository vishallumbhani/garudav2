import re
from pathlib import Path

# 1. Update Krishna engine
krishna_path = Path("src/engines/krishna/engine.py")
krishna_content = '''"""
Decision aggregator – safe version with fail‑closed and integer score.
"""

from typing import Dict, Any

class Krishna:
    def __init__(self):
        self.weights = {"bhishma": 0.5, "hanuman": 0.2, "shakuni": 0.15, "arjuna": 0.15}
        self.trace_version = "1.1"

    def run(self, request, engine_results: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Extract Hanuman and Yudhishthira info
            hanuman_info = engine_results.get("hanuman", {})
            yudhishthira_info = engine_results.get("yudhishthira", {})

            detected_secrets = hanuman_info.get("detected_secrets", [])
            secret_severity = hanuman_info.get("secret_severity")
            policy_action = yudhishthira_info.get("policy_action")

            # Default decision and score
            decision = "allow"
            score = 0
            decision_logic = "No policy or secret override"

            # Apply severity-based rules
            if secret_severity == "critical":
                decision = "block"
                score = 95
                decision_logic = "secret_severity=critical -> block"
            elif policy_action == "block":
                decision = "block"
                score = 90
                decision_logic = f"policy_action={policy_action} -> block"
            elif detected_secrets:
                decision = "challenge"
                score = 75
                decision_logic = f"detected_secrets={detected_secrets} -> challenge"

            # Ensure integer score
            score = int(round(score))

            return {
                "engine": "krishna",
                "status": "ok",
                "decision": decision,
                "score": score,
                "normalized_score": score / 100.0,
                "decision_logic": decision_logic,
                "details": {"trace": {"decision_logic": decision_logic}}
            }
        except Exception as e:
            # Fail‑closed fallback
            return {
                "engine": "krishna",
                "status": "error",
                "decision": "challenge",
                "score": 95,
                "normalized_score": 0.95,
                "decision_logic": f"krishna_error_fallback: {str(e)}",
                "details": {"trace": {"error": str(e)}}
            }
'''
krishna_path.write_text(krishna_content)
print("✅ Updated Krishna engine with safe fallback and integer score.")

# 2. Harden Sanjaya engine
sanjaya_path = Path("src/engines/sanjaya/engine.py")
sanjaya_content = '''"""
Observability / audit: writes logs and returns response, with safe defaults.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from src.core.models import ScanResponse

logger = logging.getLogger(__name__)

class Sanjaya:
    def run(self, request, krishna_result):
        # Safe extraction with fallbacks
        decision = krishna_result.get("decision", "challenge")
        score = krishna_result.get("score", 95)
        normalized_score = krishna_result.get("normalized_score", score / 100.0)
        details = krishna_result.get("details", {})
        trace = details.get("trace", {})

        # Ensure score is integer
        if isinstance(score, float):
            score = int(round(score))
        elif not isinstance(score, int):
            score = 95

        # Build final response
        response = ScanResponse(
            event_id=request.event_id,
            decision=decision,
            score=score,
            normalized_score=normalized_score,
            details=details
        )

        # Prepare audit entry
        audit_entry = {
            "event_id": request.event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": request.tenant_id,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "input_type": request.content_type,
            "decision": response.decision,
            "score": response.score,
            "normalized_score": response.normalized_score,
            "trace": trace
        }

        # Write to JSONL file
        log_path = Path("./logs/audit.jsonl")
        log_path.parent.mkdir(exist_ok=True)
        with open(log_path, "a") as f:
            f.write(json.dumps(audit_entry) + "\\n")

        return response
'''
sanjaya_path.write_text(sanjaya_content)
print("✅ Hardened Sanjaya engine with safe score conversion.")

print("\\n✅ Fixes applied. Restart the server and test.")
