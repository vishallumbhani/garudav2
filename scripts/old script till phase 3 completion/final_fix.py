#!/usr/bin/env python3
"""
Final fixes for Phase 1.2: update behavior service, Krishna, and scan_service.
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

# 1. Update behavior service
write_file("src/services/behavior_service.py", '''\
import redis
from src.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

class BehaviorTracker:
    """Lightweight session tracking using Redis."""

    def __init__(self, session_ttl=3600):
        self.session_ttl = session_ttl

    def record_request(self, session_id: str, risk_score: float):
        """Add request to session and return current stats."""
        key = f"session:{session_id}"
        pipe = redis_client.pipeline()
        pipe.lpush(key, risk_score)
        pipe.ltrim(key, 0, 99)
        pipe.expire(key, self.session_ttl)
        pipe.execute()
        scores = redis_client.lrange(key, 0, -1)
        scores = [float(s) for s in scores]
        avg_risk = sum(scores) / len(scores) if scores else 0.0
        max_risk = max(scores) if scores else 0.0
        escalation_factor = 1.0
        if max_risk >= 0.9:
            escalation_factor = 1.5
        elif len(scores) > 5 and avg_risk > 0.6:
            escalation_factor = 1.2
        return {
            "request_count": len(scores),
            "avg_risk": avg_risk,
            "max_risk": max_risk,
            "escalation_factor": escalation_factor,
            "escalation_needed": escalation_factor > 1.0
        }

tracker = BehaviorTracker()
''')

# 2. Update Krishna
write_file("src/engines/krishna/engine.py", '''\
"""
Decision aggregator with weighted scoring and policy modifiers.
"""

from typing import Dict, Any

class Krishna:
    def __init__(self):
        self.weights = {"bhishma": 0.7, "hanuman": 0.3}

    def run(self, request, engine_results: Dict[str, Any]) -> Dict[str, Any]:
        bhishma = engine_results.get("bhishma", {})
        hanuman = engine_results.get("hanuman", {})
        yudhishthira = engine_results.get("yudhishthira", {})
        behavior_modifier = engine_results.get("behavior_modifier", 1.0)

        bhishma_score = bhishma.get("score", 0.5)
        hanuman_score = hanuman.get("score", 0.5)

        weighted = (self.weights["bhishma"] * bhishma_score +
                    self.weights["hanuman"] * hanuman_score)

        policy_modifier = yudhishthira.get("modifier", 1.0)
        weighted *= policy_modifier
        weighted *= behavior_modifier
        weighted = min(weighted, 0.95)

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

# 3. Update scan_service to use behavior_modifier
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

    hanuman_result = fallback.wrap_engine("hanuman", Hanuman().run, request)
    engine_results["hanuman"] = hanuman_result

    bhishma_result = fallback.wrap_engine("bhishma", Bhishma().run, request, hanuman_result)
    engine_results["bhishma"] = bhishma_result

    # Behavior tracking: use bhishma score to update session stats and get escalation factor
    behavior_modifier = 1.0
    if request.session_id:
        stats = tracker.record_request(request.session_id, bhishma_result.get("score", 0.5))
        behavior_modifier = stats["escalation_factor"]
    engine_results["behavior_modifier"] = behavior_modifier

    yudhishthira_result = fallback.wrap_engine("yudhishthira", Yudhishthira().run, request, bhishma_result)
    engine_results["yudhishthira"] = yudhishthira_result

    krishna_result = fallback.wrap_engine("krishna", Krishna().run, request, engine_results)
    engine_results["krishna"] = krishna_result

    sanjaya = Sanjaya()
    response = sanjaya.run(request, krishna_result)

    audit_data = {
        "event_id": request.event_id,
        "tenant_id": request.tenant_id,
        "user_id": request.user_id,
        "session_id": request.session_id,
        "input_type": request.content_type,
        "decision": response.decision,
        "score": response.score,
        "normalized_score": response.normalized_score,
        "engine_results": engine_results,
        "trace": krishna_result.get("details", {}).get("trace", {})
    }

    async with AsyncSessionLocal() as db:
        await log_audit(db, audit_data)

    return response
''')

print("✅ Final fixes applied.")
print("Restart server: ./scripts/run_dev.sh")
print("Then test: ./scripts/test_api.sh")
