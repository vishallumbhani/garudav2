#!/usr/bin/env python3
"""
Phase 1.2 refinements:
- Consistent score formatting (0-100 external, 0-1 internal)
- Yudhishthira as policy modifier (not score producer)
- Benign case policy neutral
- Floating point rounding
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

def write_file(path, content):
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"Written: {file_path}")

# ----------------------------------------------------------------------
# 1. Update Yudhishthira to output policy flags and modifiers
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

        # Initial: no modifier
        modifier = 1.0
        override_action = None
        labels = []
        reason = "No policy override."

        # Check if critical patterns matched in Bhishma
        critical_matches = [m for m in bhishma_result.get("matched_patterns", []) if m.get("type") == "critical"]
        if critical_matches:
            # Policy says: critical patterns are forbidden in strict mode
            if mode == "strict":
                override_action = "block"
                labels.append("critical_pattern_block")
                reason = "Critical pattern matched: forced block."
            else:
                # In permissive, still flag but not override
                labels.append("critical_pattern_warning")
                reason = "Critical pattern matched (permissive mode)."
            # In any case, we can apply a modifier to increase risk
            modifier = 1.5

        # Check sensitive patterns
        sensitive_matches = [m for m in bhishma_result.get("matched_patterns", []) if m.get("type") == "sensitive"]
        if sensitive_matches:
            if mode == "strict":
                modifier = max(modifier, 1.2)
                labels.append("strict_mode_sensitive")
                reason = "Strict mode: sensitive data escalates risk."
            else:
                labels.append("sensitive_data_warning")

        # If no modifiers, keep modifier = 1.0 and no override
        # For benign, we output nothing

        return {
            "engine": "yudhishthira",
            "status": "ok",
            "modifier": round(modifier, 2),
            "override_action": override_action,
            "labels": labels,
            "reason": reason
        }
''')

# ----------------------------------------------------------------------
# 2. Update Krishna to incorporate Yudhishthira's modifier
write_file("src/engines/krishna/engine.py", '''\
"""
Decision aggregator with weighted scoring and policy modifiers.
"""

from typing import Dict, Any

class Krishna:
    def __init__(self):
        # Weights: bhishma (rule) highest, then hanuman (triage), then no yudhishthira score
        self.weights = {"bhishma": 0.7, "hanuman": 0.3}

    def run(self, request, engine_results: Dict[str, Any]) -> Dict[str, Any]:
        bhishma = engine_results.get("bhishma", {})
        hanuman = engine_results.get("hanuman", {})
        yudhishthira = engine_results.get("yudhishthira", {})

        bhishma_score = bhishma.get("score", 0.5)
        hanuman_score = hanuman.get("score", 0.5)

        # Weighted base score
        weighted = (self.weights["bhishma"] * bhishma_score +
                    self.weights["hanuman"] * hanuman_score)

        # Apply policy modifier from Yudhishthira
        modifier = yudhishthira.get("modifier", 1.0)
        weighted *= modifier
        weighted = min(weighted, 0.95)   # cap

        # Check for policy override
        override_action = yudhishthira.get("override_action")
        if override_action:
            decision = override_action
        else:
            if weighted >= 0.8:
                decision = "block"
            elif weighted >= 0.6:
                decision = "challenge"
            elif weighted >= 0.3:
                decision = "monitor"
            else:
                decision = "allow"

        # Build trace
        trace = {
            "weights": self.weights,
            "scores": {
                "bhishma": round(bhishma_score, 3),
                "hanuman": round(hanuman_score, 3)
            },
            "policy_modifier": round(modifier, 2),
            "weighted_score": round(weighted, 3),
            "decision_logic": f"score={weighted:.3f} -> {decision}"
        }
        if override_action:
            trace["override"] = override_action

        # Convert to integer percentage for external score
        external_score = int(round(weighted * 100))

        return {
            "engine": "krishna",
            "score": external_score,
            "normalized_score": round(weighted, 3),
            "decision": decision,
            "details": {"trace": trace}
        }
''')

# ----------------------------------------------------------------------
# 3. Update response model to include normalized_score
write_file("src/core/models.py", '''\
from pydantic import BaseModel
from typing import Any, Dict, Optional, Union
from datetime import datetime

class ScanRequest(BaseModel):
    content_type: str
    content: Union[str, bytes]
    filename: Optional[str] = None
    tenant_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source: str
    event_id: str
    timestamp: datetime
    normalized_text: Optional[str] = None
    file_metadata: Optional[Dict[str, Any]] = None

class ScanResponse(BaseModel):
    event_id: str
    decision: str
    score: int            # 0-100 external
    normalized_score: float  # 0.0-1.0 internal
    details: Dict[str, Any]

class EngineResult(BaseModel):
    engine_name: str
    score: int
    details: Dict[str, Any]
''')

# ----------------------------------------------------------------------
# 4. Update Sanjaya to use new model
write_file("src/engines/sanjaya/engine.py", '''\
"""
Observability / audit.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from src.core.models import ScanResponse

logger = logging.getLogger(__name__)

class Sanjaya:
    def run(self, request, krishna_result):
        # Build final response
        response = ScanResponse(
            event_id=request.event_id,
            decision=krishna_result["decision"],
            score=krishna_result["score"],
            normalized_score=krishna_result["normalized_score"],
            details=krishna_result["details"]
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
            "trace": krishna_result["details"].get("trace", {})
        }

        # Write to JSONL file
        log_path = Path("./logs/audit.jsonl")
        log_path.parent.mkdir(exist_ok=True)
        with open(log_path, "a") as f:
            f.write(json.dumps(audit_entry) + "\\n")

        return response
''')

# ----------------------------------------------------------------------
# 5. Update scan_service to pass Yudhishthira result correctly
#    (no change needed, but ensure we pass engine_results dict)
# The existing scan_service already does that; we just need to ensure
# that the key 'yudhishthira' is present. We'll update _run_pipeline to
# store engine_results['yudhishthira'] as the output of Yudhishthira.
# The current scan_service already does that via fallback.wrap_engine.
# No change required.

# ----------------------------------------------------------------------
print("✅ Phase 1.2 refinements applied.")
print("Now restart the server: ./scripts/run_dev.sh")
print("Then test: ./scripts/test_api.sh")
