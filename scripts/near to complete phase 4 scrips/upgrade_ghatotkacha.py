#!/usr/bin/env python3
"""
Upgrade Ghatotkacha (session intelligence) with:
- Anomaly thresholds
- Session classification
- Enhanced scoring with decay and spikes
"""

import os
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

def write_file(path, content):
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"Written: {file_path}")

# 1. New behavior service with full session intelligence
new_behavior_service = '''import redis
import math
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from src.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

class Ghatotkacha:
    """
    Full session intelligence: tracks request history, computes anomaly scores,
    classifies sessions, and provides escalation factors.
    """

    def __init__(self, session_ttl=3600, window_size=10):
        self.session_ttl = session_ttl
        self.window_size = window_size  # number of recent requests to analyze

        # Thresholds for classification (normalized scores 0-1)
        self.thresholds = {
            "clean": 0.3,
            "suspicious": 0.6,
            "malicious": 0.8,
            "compromised": 0.95
        }

    def record_request(self, session_id: str, risk_score: float) -> Dict[str, Any]:
        if not session_id:
            return self._empty_stats()

        key = f"session:{session_id}"
        now = datetime.now(timezone.utc).timestamp()

        # Store request with timestamp and risk
        pipe = redis_client.pipeline()
        pipe.zadd(key, {f"{now}:{risk_score}": now})  # Use sorted set by timestamp
        pipe.zremrangebyrank(key, 0, -self.window_size - 1)  # keep last N
        pipe.expire(key, self.session_ttl)
        pipe.execute()

        # Retrieve recent requests
        recent = redis_client.zrange(key, 0, -1, withscores=True)
        # Each entry format: "timestamp:risk"
        scores = []
        timestamps = []
        for entry, ts in recent:
            try:
                _, risk = entry.split(':')
                scores.append(float(risk))
                timestamps.append(float(ts))
            except:
                continue

        if not scores:
            return self._empty_stats()

        # Compute statistics
        n = len(scores)
        mean = sum(scores) / n
        # Standard deviation (sample)
        if n > 1:
            variance = sum((x - mean) ** 2 for x in scores) / (n - 1)
            std = math.sqrt(variance)
        else:
            std = 0

        # Simple anomaly: if last score > mean + 2*std, flag spike
        last_score = scores[-1]
        spike = last_score > (mean + 2 * std) if n > 1 else False

        # Exponential decay of historical scores to compute recent weighted average
        # More weight to recent requests
        if n > 0:
            weights = [math.exp(-0.3 * (n - i - 1)) for i in range(n)]
            total_weight = sum(weights)
            weighted_risk = sum(score * w for score, w in zip(scores, weights)) / total_weight
        else:
            weighted_risk = 0.0

        # Determine session classification
        classification = "clean"
        if weighted_risk >= self.thresholds["compromised"]:
            classification = "compromised"
        elif weighted_risk >= self.thresholds["malicious"]:
            classification = "malicious"
        elif weighted_risk >= self.thresholds["suspicious"]:
            classification = "suspicious"

        # Compute escalation factor based on classification and spike
        base_factor = {
            "clean": 1.0,
            "suspicious": 1.2,
            "malicious": 1.5,
            "compromised": 2.0
        }.get(classification, 1.0)

        # Extra spike boost
        spike_factor = 1.3 if spike else 1.0
        escalation_factor = base_factor * spike_factor
        escalation_factor = min(escalation_factor, 2.5)

        # Build reason
        reason = f"Session {classification}"
        if spike:
            reason += f" (risk spike detected: last={last_score:.2f}, mean={mean:.2f})"
        else:
            reason += f" (weighted risk={weighted_risk:.2f})"

        return {
            "escalation_factor": round(escalation_factor, 2),
            "escalation_reason": reason,
            "request_count": n,
            "avg_risk": round(mean, 3),
            "max_risk": round(max(scores), 3),
            "weighted_risk": round(weighted_risk, 3),
            "classification": classification,
            "spike_detected": spike,
            "last_risk": round(last_score, 3)
        }

    def _empty_stats(self):
        return {
            "escalation_factor": 1.0,
            "escalation_reason": "no session",
            "request_count": 0,
            "avg_risk": 0,
            "max_risk": 0,
            "weighted_risk": 0,
            "classification": "none",
            "spike_detected": False,
            "last_risk": 0
        }

# Keep the tracker instance name for compatibility
tracker = Ghatotkacha()
'''
write_file("src/services/behavior_service.py", new_behavior_service)

# 2. Update Krishna to include the new fields in trace
# We'll modify the run method to incorporate classification and spike info
with open("src/engines/krishna/engine.py", "r") as f:
    krishna = f.read()

# Ensure we extract and include classification and spike fields
# Find the part where behavior is extracted
if "behavior = engine_results.get(\"behavior\", {})" in krishna:
    # Add extraction of new fields
    insert_after = "behavior = engine_results.get(\"behavior\", {})"
    new_lines = """
        behavior_classification = behavior.get(\"classification\", \"unknown\")
        behavior_spike = behavior.get(\"spike_detected\", False)
        behavior_weighted_risk = behavior.get(\"weighted_risk\", 0.0)
"""
    krishna = krishna.replace(insert_after, insert_after + new_lines)

    # Now add these fields to the trace dict
    # Find the trace = { line and insert after it
    trace_start = "trace = {"
    trace_insert = """            "session_classification": behavior_classification,
            "session_spike_detected": behavior_spike,
            "session_weighted_risk": behavior_weighted_risk,
"""
    krishna = krishna.replace(trace_start, trace_start + "\n" + trace_insert)

    write_file("src/engines/krishna/engine.py", krishna)
    print("✅ Updated Krishna trace with session classification.")

print("✅ Ghatotkacha upgraded with anomaly detection and session classification.")
print("Restart server and run tests to verify.")
