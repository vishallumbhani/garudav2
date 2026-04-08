#!/usr/bin/env python3
"""
Tighten session intelligence:
- Use max risk and high‑risk count alongside weighted average
- Apply decay to keep risk elevated after malicious events
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

new_behavior = '''import redis
import math
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from src.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

class Ghatotkacha:
    """
    Session intelligence with:
    - Weighted average with decay
    - Max risk tracking
    - High‑risk event count
    - Escalation based on worst‑case behavior
    """

    def __init__(self, session_ttl=3600, window_size=20):
        self.session_ttl = session_ttl
        self.window_size = window_size

        # Thresholds for classification (based on weighted risk)
        self.thresholds = {
            "clean": 0.3,
            "suspicious": 0.6,
            "malicious": 0.8,
            "compromised": 0.95
        }

        # High‑risk threshold (any request above this is considered high‑risk)
        self.high_risk_threshold = 0.6

    def record_request(self, session_id: str, risk_score: float) -> Dict[str, Any]:
        if not session_id:
            return self._empty_stats()

        key = f"session:{session_id}"
        now = datetime.now(timezone.utc).timestamp()

        # Store with timestamp
        pipe = redis_client.pipeline()
        pipe.zadd(key, {f"{now}:{risk_score}": now})
        pipe.zremrangebyrank(key, 0, -self.window_size - 1)  # keep last N
        pipe.expire(key, self.session_ttl)
        pipe.execute()

        # Retrieve all entries
        entries = redis_client.zrange(key, 0, -1, withscores=True)
        scores = []
        timestamps = []
        for entry, ts in entries:
            try:
                _, risk = entry.split(':')
                scores.append(float(risk))
                timestamps.append(float(ts))
            except:
                continue

        if not scores:
            return self._empty_stats()

        n = len(scores)

        # Weighted average with exponential decay (more weight to recent)
        if n > 0:
            # Decay factor: give higher weight to recent requests
            weights = [math.exp(-0.2 * (n - i - 1)) for i in range(n)]
            total_weight = sum(weights)
            weighted_risk = sum(score * w for score, w in zip(scores, weights)) / total_weight
        else:
            weighted_risk = 0.0

        # Max risk ever seen
        max_risk = max(scores)

        # Count of high‑risk events
        high_risk_count = sum(1 for s in scores if s >= self.high_risk_threshold)

        # Combined risk: weighted average + max risk boost
        # If max risk is high, even if weighted average is low, the session is risky
        combined_risk = max(weighted_risk, max_risk * 0.8)

        # Determine classification based on combined risk
        classification = "clean"
        if combined_risk >= self.thresholds["compromised"]:
            classification = "compromised"
        elif combined_risk >= self.thresholds["malicious"]:
            classification = "malicious"
        elif combined_risk >= self.thresholds["suspicious"]:
            classification = "suspicious"

        # Compute escalation factor
        base_factor = {
            "clean": 1.0,
            "suspicious": 1.2,
            "malicious": 1.5,
            "compromised": 2.0
        }.get(classification, 1.0)

        # Additional boost for repeated high‑risk events
        if high_risk_count > 1:
            repetition_boost = min(1 + (high_risk_count - 1) * 0.1, 1.5)
            base_factor *= repetition_boost

        escalation_factor = min(base_factor, 2.5)

        # Build reason
        reason = f"Session {classification}"
        if max_risk >= self.high_risk_threshold:
            reason += f" (max risk {max_risk:.2f}, {high_risk_count} high-risk events)"
        else:
            reason += f" (weighted risk {weighted_risk:.2f})"

        return {
            "escalation_factor": round(escalation_factor, 2),
            "escalation_reason": reason,
            "request_count": n,
            "avg_risk": round(sum(scores)/n, 3),
            "max_risk": round(max_risk, 3),
            "weighted_risk": round(weighted_risk, 3),
            "combined_risk": round(combined_risk, 3),
            "classification": classification,
            "high_risk_count": high_risk_count,
            "spike_detected": risk_score > (sum(scores)/n + 2 * math.sqrt(sum((s - sum(scores)/n)**2 for s in scores)/(n-1)) if n>1 else 0),
            "last_risk": round(risk_score, 3)
        }

    def _empty_stats(self):
        return {
            "escalation_factor": 1.0,
            "escalation_reason": "no session",
            "request_count": 0,
            "avg_risk": 0,
            "max_risk": 0,
            "weighted_risk": 0,
            "combined_risk": 0,
            "classification": "none",
            "high_risk_count": 0,
            "spike_detected": False,
            "last_risk": 0
        }

tracker = Ghatotkacha()
'''
write_file("src/services/behavior_service.py", new_behavior)

# Also update Krishna trace to include the new fields if desired
with open("src/engines/krishna/engine.py", "r") as f:
    krishna = f.read()

# Add new fields to trace (combined_risk, high_risk_count, max_risk)
if "behavior_classification" in krishna:
    # Ensure we extract them from behavior dict
    extra_fields = """
        behavior_combined_risk = behavior.get(\"combined_risk\", 0.0)
        behavior_high_risk_count = behavior.get(\"high_risk_count\", 0)
        behavior_max_risk = behavior.get(\"max_risk\", 0.0)
"""
    if "behavior_combined_risk" not in krishna:
        krishna = krishna.replace("behavior_classification = behavior.get(\"classification\", \"unknown\")",
                                  "behavior_classification = behavior.get(\"classification\", \"unknown\")\n" + extra_fields)

    # Add to trace dict
    trace_insert = """            "session_combined_risk": behavior_combined_risk,
            "session_high_risk_count": behavior_high_risk_count,
            "session_max_risk": behavior_max_risk,
"""
    # Insert after session_weighted_risk line
    krishna = krishna.replace('"session_weighted_risk": behavior_weighted_risk,', '"session_weighted_risk": behavior_weighted_risk,\n' + trace_insert)
    write_file("src/engines/krishna/engine.py", krishna)
    print("✅ Updated Krishna trace with combined risk and high-risk count.")

print("✅ Ghatotkacha tightened with max risk and high-risk count.")
print("Restart server and test with multiple malicious requests.")
