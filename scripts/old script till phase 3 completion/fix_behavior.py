#!/usr/bin/env python3
"""
Fix behavior tracking integration:
- Use actual risk score (from bhishma or weighted) for tracking.
- Apply behavior modifier in Krishna, not in scan_service.
- Ensure behavior modifier is only applied when escalation is warranted.
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
# 1. Update behavior service with better logic
write_file("src/services/behavior_service.py", '''\
import redis
from src.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

class BehaviorTracker:
    """Track session behavior and return escalation factor."""

    def __init__(self, session_ttl=3600):
        self.session_ttl = session_ttl

    def record_request(self, session_id: str, risk_score: float):
        """Record a request's risk score and return stats."""
        if not session_id:
            return {"escalation_factor": 1.0, "request_count": 0, "avg_risk": 0}
        key = f"session:{session_id}"
        pipe = redis_client.pipeline()
        pipe.lpush(key, risk_score)
        pipe.ltrim(key, 0, 99)   # keep last 100 requests
        pipe.expire(key, self.session_ttl)
        pipe.execute()
        # Get stats
        scores = redis_client.lrange(key, 0, -1)
        scores = [float(s) for s in scores]
        avg_risk = sum(scores) / len(scores) if scores else 0.0
        max_risk = max(scores) if scores else 0.0
        # Escalate if:
        # - more than 3 requests with avg risk > 0.6, or
        # - any request with risk > 0.9
        escalation_needed = (len(scores) > 3 and avg_risk > 0.6) or (max_risk > 0.9)
        escalation_factor = 1.5 if escalation_needed else 1.0
        return {
            "escalation_factor": escalation_factor,
            "request_count": len(scores),
            "avg_risk": avg_risk,
            "max_risk": max_risk
        }

tracker = BehaviorTracker()
''')

# ----------------------------------------------------------------------
# 2. Update scan_service to remove the old behavior adjustment line
#    and instead pass the risk to Krishna via engine_results.
write_file("src/services/scan_service.py", '''\
import asyncio
from pathlib import Path
from src.core.models import ScanRequest, ScanResponse
from src.utils.file_extractors import extract_from_file
from src.engines.hanuman.engine import Hanuman
from src.engines.bhishma.engine import Bhishma
from src.engines.yudhishthira.engine import Yudhishthira
from src.engines.krishna.engine import Krishna
from src.engines.sanjaya.engine import Sanjaya
from src.services.audit_service import log_audit
from src.services.behavior_service import tracker
from src.core.fallback import fallback
from src.db.base import AsyncSessionLocal

async def scan_text(request: ScanRequest) -> ScanResponse:
    request.normalized_text = request.content if isinstance(request.content, str) else request.content.decode('utf-8', errors='ignore')
    return await _run_pipeline(request)

async def scan_file(request: ScanRequest) -> ScanResponse:
    temp_file = Path("/tmp") / f"garuda_{request.event_id}.tmp"
    temp_file.write_bytes(request.content)
    try:
        extraction = extract_from_file(temp_file, request.content, request.filename or "unknown")
        request.normalized_text = extraction["normalized_text"]
        request.file_metadata = extraction["metadata"]
    finally:
        temp_file.unlink(missing_ok=True)
    return await _run_pipeline(request)

async def _run_pipeline(request) -> ScanResponse:
    engine_results = {}

    # Run Hanuman
    hanuman_result = fallback.wrap_engine("hanuman", Hanuman().run, request)
    engine_results["hanuman"] = hanuman_result

    # Run Bhishma
    bhishma_result = fallback.wrap_engine("bhishma", Bhishma().run, request, hanuman_result)
    engine_results["bhishma"] = bhishma_result

    # Run Yudhishthira
    yudhishthira_result = fallback.wrap_engine("yudhishthira", Yudhishthira().run, request, bhishma_result)
    engine_results["yudhishthira"] = yudhishthira_result

    # Behavior tracking: use the raw risk (e.g., bhishma score) to update session stats
    if request.session_id:
        # Use the bhishma score as the risk for this request
        risk_score = bhishma_result.get("score", 0.5)
        stats = tracker.record_request(request.session_id, risk_score)
        # Store behavior stats in engine_results for Krishna to use
        engine_results["behavior"] = {
            "engine": "behavior",
            "status": "ok",
            "escalation_factor": stats["escalation_factor"],
            "request_count": stats["request_count"],
            "avg_risk": stats["avg_risk"]
        }
    else:
        engine_results["behavior"] = {"escalation_factor": 1.0}

    # Run Krishna
    krishna_result = fallback.wrap_engine("krishna", Krishna().run, request, engine_results)
    engine_results["krishna"] = krishna_result

    # Sanjaya builds final response
    sanjaya = Sanjaya()
    response = sanjaya.run(request, krishna_result)

    # Prepare audit data
    audit_data = {
        "event_id": request.event_id,
        "tenant_id": request.tenant_id,
        "user_id": request.user_id,
        "session_id": request.session_id,
        "input_type": request.content_type,
        "decision": response.decision,
        "final_score": response.score,
        "normalized_score": response.normalized_score,
        "engine_results": engine_results,
        "trace": krishna_result.get("details", {}).get("trace", {})
    }

    async with AsyncSessionLocal() as db:
        await log_audit(db, audit_data)

    return response
''')

# ----------------------------------------------------------------------
# 3. Update Krishna to incorporate behavior escalation factor
write_file("src/engines/krishna/engine.py", '''\
"""
Decision aggregator with weighted scoring, policy modifier, and behavior escalation.
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
        weighted = (self.weights["bhishma"] * bhishma_score +
                    self.weights["hanuman"] * hanuman_score)

        # Apply policy modifier from Yudhishthira
        policy_modifier = yudhishthira.get("modifier", 1.0)
        weighted *= policy_modifier

        # Apply behavior escalation factor
        behavior_modifier = behavior.get("escalation_factor", 1.0)
        weighted *= behavior_modifier

        # Cap at 0.95
        weighted = min(weighted, 0.95)

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
            "policy_modifier": round(policy_modifier, 2),
            "behavior_modifier": round(behavior_modifier, 2),
            "weighted_score": round(weighted, 3),
            "decision_logic": f"score={weighted:.3f} -> {decision}"
        }
        if override_action:
            trace["override"] = override_action

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
print("✅ Behavior tracking fixed.")
print("Restart server and test again.")
