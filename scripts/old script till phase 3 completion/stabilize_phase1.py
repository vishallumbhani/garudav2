#!/usr/bin/env python3
"""
Phase 1.1 Stabilization: add fallback, improved Krishna, behavior tracking,
structured trace, enhanced rules, safe defaults.
"""

import os
import sys
from pathlib import Path

# Project root (assuming script is in scripts/)
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

def write_file(path, content):
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"Written: {file_path}")

# ----------------------------------------------------------------------
# 1. Fallback Manager
write_file("src/core/fallback.py", '''\
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class FallbackManager:
    """Handle engine failures, mark degraded mode, enforce safe defaults."""

    def __init__(self, safe_mode: bool = True):
        self.safe_mode = safe_mode
        self.degraded_engines = set()

    def wrap_engine(self, engine_name: str, func, *args, **kwargs):
        """Execute an engine with fallback."""
        try:
            result = func(*args, **kwargs)
            # Ensure result has required fields
            if not isinstance(result, dict):
                raise ValueError(f"Engine {engine_name} returned non-dict")
            result.setdefault("status", "ok")
            return result
        except Exception as e:
            logger.error(f"Engine {engine_name} failed: {e}")
            self.degraded_engines.add(engine_name)
            # Return degraded result
            return {
                "engine": engine_name,
                "status": "degraded",
                "score": 0.5,   # neutral, but will be escalated
                "confidence": 0.0,
                "labels": ["engine_failure"],
                "reason": f"Engine {engine_name} failed: {str(e)}",
                "error": str(e)
            }

    def get_safe_decision(self, final_score: float) -> str:
        """Return safe default decision based on degraded state."""
        if self.safe_mode:
            # If any engine is degraded, never allow
            if self.degraded_engines:
                return "challenge"  # or "monitor", but challenge is safer
        if final_score >= 0.8:
            return "block"
        elif final_score >= 0.6:
            return "challenge"
        elif final_score >= 0.3:
            return "monitor"
        else:
            return "allow"

fallback = FallbackManager()
''')

# ----------------------------------------------------------------------
# 2. Improved Krishna
write_file("src/engines/krishna/engine.py", '''\
"""
Decision aggregator with weighted scoring and explainability.
"""

from typing import Dict, Any

class Krishna:
    def __init__(self):
        # Weights: bhishma (rule) highest, then hanuman (triage), then policy adjustment
        self.weights = {"bhishma": 0.6, "hanuman": 0.2, "yudhishthira": 0.2}

    def run(self, request, engine_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combine engine scores, produce final decision and trace.
        """
        bhishma = engine_results.get("bhishma", {})
        hanuman = engine_results.get("hanuman", {})
        yudhishthira = engine_results.get("yudhishthira", {})

        # Extract scores (default to 0.5 if missing)
        bhishma_score = bhishma.get("score", 0.5)
        hanuman_score = hanuman.get("score", 0.5)
        yudhishthira_score = yudhishthira.get("score", 0.5)

        # Weighted score
        weighted = (self.weights["bhishma"] * bhishma_score +
                    self.weights["hanuman"] * hanuman_score +
                    self.weights["yudhishthira"] * yudhishthira_score)

        # Apply safety: if any engine is degraded, escalate
        if any(r.get("status") == "degraded" for r in engine_results.values()):
            weighted = min(weighted + 0.2, 0.95)   # increase risk
            escalation_reason = "degraded_engine"
        else:
            escalation_reason = None

        # Determine decision
        if weighted >= 0.8:
            decision = "block"
        elif weighted >= 0.6:
            decision = "challenge"
        elif weighted >= 0.3:
            decision = "monitor"
        else:
            decision = "allow"

        # Build trace for explainability
        trace = {
            "weights": self.weights,
            "scores": {
                "bhishma": bhishma_score,
                "hanuman": hanuman_score,
                "yudhishthira": yudhishthira_score
            },
            "weighted_score": weighted,
            "decision_logic": f"score={weighted:.2f} -> {decision}"
        }
        if escalation_reason:
            trace["escalation"] = escalation_reason

        # Convert to integer percentage for response (0-100)
        int_score = int(round(weighted * 100))

        return {
            "engine": "krishna",
            "score": int_score,
            "decision": decision,
            "details": {"trace": trace}
        }
''')

# ----------------------------------------------------------------------
# 3. Update Hanuman to new schema
write_file("src/engines/hanuman/engine.py", '''\
"""
Fast triage engine with enhanced checks.
"""

import re
from typing import Dict, Any, List

class Hanuman:
    def run(self, request) -> Dict[str, Any]:
        if request.normalized_text is not None:
            text = request.normalized_text
        else:
            text = request.content
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='ignore')

        score = 0.0
        labels = []
        reason = "Fast triage completed."

        # 1. Long input
        if len(text) > 5000:
            score += 0.2
            labels.append("long_input")
            reason += " Input is long."

        # 2. Suspicious density of security-sensitive words
        sensitive_words = ["secret", "token", "password", "key", "auth", "credential", "api_key", "private_key"]
        sensitive_count = sum(text.lower().count(word) for word in sensitive_words)
        density = sensitive_count / max(1, len(text)/1000)  # per 1000 chars
        if density > 2:
            score += 0.25
            labels.append("high_density_sensitive")
            reason += " High density of sensitive terms."
        elif density > 0.5:
            score += 0.1
            labels.append("moderate_density_sensitive")

        # 3. Likely secret markers
        secret_patterns = [
            r"-----BEGIN (RSA|OPENSSH|DSA|EC) PRIVATE KEY-----",
            r"Bearer\s+[A-Za-z0-9_\-\.]+",
            r"Authorization:\s*Basic\s+[A-Za-z0-9+/=]+",
            r"sk-[A-Za-z0-9]{32,}",
        ]
        for pattern in secret_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.35
                labels.append("secret_marker_detected")
                reason += " Secret marker found."
                break

        # 4. Repeated instruction phrases (injection attempts)
        injection_phrases = ["ignore previous instructions", "reveal system prompt", "forget all rules", "act as"]
        for phrase in injection_phrases:
            if phrase.lower() in text.lower():
                score += 0.3
                labels.append("injection_attempt")
                reason += f" Injection phrase: '{phrase}'."
                break

        # 5. Low-information / junk input
        if len(text.strip()) < 10:
            score += 0.1
            labels.append("short_input")
        if len(set(text)) < 20:  # many repeated chars
            score += 0.05
            labels.append("low_entropy")

        # Cap score at 0.95
        score = min(score, 0.95)

        return {
            "engine": "hanuman",
            "status": "ok",
            "score": round(score, 2),
            "confidence": 0.9,
            "labels": labels,
            "reason": reason
        }
''')

# ----------------------------------------------------------------------
# 4. Update Bhishma to new schema
write_file("src/engines/bhishma/engine.py", '''\
"""
Rule engine (regex/keyword) with YAML configuration.
"""

import re
import yaml
from pathlib import Path
from typing import Dict, Any, List

class Bhishma:
    def __init__(self):
        self.rules = {"critical": [], "sensitive": [], "warning": []}
        rules_path = Path(__file__).parent / "rules.yaml"
        if rules_path.exists():
            with open(rules_path) as f:
                data = yaml.safe_load(f)
                self.rules = {
                    "critical": data.get("critical_patterns", []),
                    "sensitive": data.get("sensitive_patterns", []),
                    "warning": data.get("warning_patterns", [])
                }

    def run(self, request, hanuman_result) -> Dict[str, Any]:
        if request.normalized_text is not None:
            text = request.normalized_text
        else:
            text = request.content
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='ignore')

        matched = []
        highest_score = 0.0
        reason = ""

        # Check critical patterns first (highest impact)
        for pattern_info in self.rules.get("critical", []):
            if re.search(pattern_info["pattern"], text, re.IGNORECASE):
                matched.append(pattern_info)
                highest_score = max(highest_score, pattern_info["severity"])
                reason = f"Critical pattern: {pattern_info['pattern']}"

        # If no critical, check sensitive
        if not matched:
            for pattern_info in self.rules.get("sensitive", []):
                if re.search(pattern_info["pattern"], text, re.IGNORECASE):
                    matched.append(pattern_info)
                    highest_score = max(highest_score, pattern_info["severity"])
                    reason = f"Sensitive pattern: {pattern_info['pattern']}"

        # If still no match, check warning
        if not matched:
            for pattern_info in self.rules.get("warning", []):
                if re.search(pattern_info["pattern"], text, re.IGNORECASE):
                    matched.append(pattern_info)
                    highest_score = max(highest_score, pattern_info["severity"])
                    reason = f"Warning pattern: {pattern_info['pattern']}"

        if not matched:
            highest_score = 0.1
            reason = "No patterns matched."

        return {
            "engine": "bhishma",
            "status": "ok",
            "score": round(highest_score, 2),
            "confidence": 0.8 if highest_score > 0.5 else 0.6,
            "labels": [p.get("type", "unknown") for p in matched],
            "reason": reason,
            "matched_patterns": matched
        }
''')

# ----------------------------------------------------------------------
# 5. Update Yudhishthira to new schema
write_file("src/engines/yudhishthira/engine.py", '''\
"""
Policy/tenant engine with simple overrides.
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

        original_score = bhishma_result["score"]
        adjusted_score = original_score
        labels = []
        reason = "No policy override."

        critical_matches = [m for m in bhishma_result.get("matched_patterns", []) if m.get("type") == "critical"]
        if critical_matches:
            adjusted_score = 0.95
            labels.append("critical_pattern_block")
            reason = "Critical pattern matched: forced block."

        sensitive_matches = [m for m in bhishma_result.get("matched_patterns", []) if m.get("type") == "sensitive"]
        if sensitive_matches:
            if mode == "strict":
                adjusted_score = max(adjusted_score, 0.8)
                labels.append("strict_mode_override")
                reason = "Strict mode: sensitive data overrides."
            else:
                labels.append("sensitive_data_warning")

        if adjusted_score >= policy["block_threshold"]:
            labels.append("block_by_threshold")
            reason += f" Score above {policy['block_threshold']} triggers block."

        return {
            "engine": "yudhishthira",
            "status": "ok",
            "score": round(adjusted_score, 2),
            "confidence": 0.7,
            "labels": labels,
            "reason": reason
        }
''')

# ----------------------------------------------------------------------
# 6. Update Sanjaya to new schema and trace
write_file("src/engines/sanjaya/engine.py", '''\
"""
Observability / audit: writes logs and returns response.
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
            details=krishna_result["details"]
        )

        # Prepare audit entry with full trace
        audit_entry = {
            "event_id": request.event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": request.tenant_id,
            "user_id": request.user_id,
            "session_id": request.session_id,
            "input_type": request.content_type,
            "decision": response.decision,
            "final_score": response.score,
            "engine_results": {
                # We'll inject these later in scan_service; for now empty
            },
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
# 7. Behavior tracking service (Ghatotkacha-lite)
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
        pipe.ltrim(key, 0, 99)   # keep last 100 requests
        pipe.expire(key, self.session_ttl)
        pipe.execute()
        # Get stats
        scores = redis_client.lrange(key, 0, -1)
        scores = [float(s) for s in scores]
        avg_risk = sum(scores) / len(scores) if scores else 0.0
        max_risk = max(scores) if scores else 0.0
        return {
            "request_count": len(scores),
            "avg_risk": avg_risk,
            "max_risk": max_risk,
            "escalation_needed": max_risk >= 0.9 or (len(scores) > 5 and avg_risk > 0.6)
        }

    def get_escalation_factor(self, session_id: str) -> float:
        """Return factor to multiply risk (1.0 = no escalation)."""
        stats = self.record_request(session_id, 0)  # dummy record, we'll update after score
        if stats["escalation_needed"]:
            return 1.5
        return 1.0

tracker = BehaviorTracker()
''')

# ----------------------------------------------------------------------
# 8. Enhanced Bhishma rules
write_file("src/engines/bhishma/rules.yaml", '''\
critical_patterns:
  - pattern: '(?i)(ignore|disregard|forget) previous instructions'
    severity: 0.95
    type: critical
  - pattern: '(?i)reveal (system|base) prompt'
    severity: 0.95
    type: critical
  - pattern: '(?i)-----BEGIN (RSA|OPENSSH|DSA|EC) PRIVATE KEY-----'
    severity: 0.95
    type: critical
  - pattern: '(?i)Bearer [A-Za-z0-9_\-\.]{20,}'
    severity: 0.95
    type: critical
  - pattern: 'sk-[A-Za-z0-9]{32,}'
    severity: 0.95
    type: critical
  - pattern: '(?i)(api[_-]?key|token)[=: ]+[A-Za-z0-9]{10,}'
    severity: 0.95
    type: critical

sensitive_patterns:
  - pattern: '(?i)password'
    severity: 0.60
    type: sensitive
  - pattern: '(?i)secret'
    severity: 0.60
    type: sensitive
  - pattern: '(?i)api[_-]?key'
    severity: 0.60
    type: sensitive
  - pattern: '(?i)token'
    severity: 0.60
    type: sensitive
  - pattern: '(?i)ssh-rsa'
    severity: 0.60
    type: sensitive
  - pattern: '(?i)credit card'
    severity: 0.60
    type: sensitive
  - pattern: '(?i)social security'
    severity: 0.60
    type: sensitive

warning_patterns:
  - pattern: '(?i)confidential'
    severity: 0.30
    type: warning
  - pattern: '(?i)internal use only'
    severity: 0.30
    type: warning
  - pattern: '(?i)do not share'
    severity: 0.30
    type: warning
''')

# ----------------------------------------------------------------------
# 9. Update scan_service to integrate fallback and behavior tracking
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
    # Initialize engine results dict
    engine_results = {}

    # Run Hanuman with fallback
    hanuman_result = fallback.wrap_engine("hanuman", Hanuman().run, request)
    engine_results["hanuman"] = hanuman_result

    # Run Bhishma
    bhishma_result = fallback.wrap_engine("bhishma", Bhishma().run, request, hanuman_result)
    engine_results["bhishma"] = bhishma_result

    # Run Yudhishthira
    yudhishthira_result = fallback.wrap_engine("yudhishthira", Yudhishthira().run, request, bhishma_result)
    engine_results["yudhishthira"] = yudhishthira_result

    # Behavior tracking: get session stats and adjust risk
    if request.session_id:
        stats = tracker.record_request(request.session_id, bhishma_result.get("score", 0.5))
        # Optionally adjust krishna input based on escalation
        # We'll pass stats to Krishna via an additional parameter? For simplicity, modify yudhishthira score.
        if stats.get("escalation_needed"):
            engine_results["yudhishthira"]["score"] = min(engine_results["yudhishthira"]["score"] * 1.2, 0.95)

    # Run Krishna
    krishna_result = fallback.wrap_engine("krishna", Krishna().run, request, engine_results)
    engine_results["krishna"] = krishna_result

    # Sanjaya builds the final response
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
        "engine_results": engine_results,
        "trace": krishna_result.get("details", {}).get("trace", {})
    }

    # Log asynchronously
    async with AsyncSessionLocal() as db:
        await log_audit(db, audit_data)

    return response
''')

# ----------------------------------------------------------------------
# 10. Update main.py to include health (already there, but ensure)
write_file("src/api/main.py", '''\
from fastapi import FastAPI
from src.api.routes import scan_text, scan_file

app = FastAPI(title="Garuda Local")

app.include_router(scan_text.router)
app.include_router(scan_file.router)

@app.get("/v1/health")
async def health():
    return {"status": "ok"}
''')

# ----------------------------------------------------------------------
print("✅ Phase 1.1 stabilization complete.")
print("Run ./scripts/run_dev.sh to test the improved pipeline.")
print("The system now includes fallback, weighted scoring, behavior tracking, and enhanced rules.")
