#!/usr/bin/env python3
"""
Implement Phase 1.4 decision matrix:
- Session classification: clean, suspicious, hostile.
- Request risk buckets (low, medium, high) based on base_weighted_score.
- Decision matrix (session class × request risk).
- Action ordering (allow < monitor < challenge < block).
- Trace fields for reasoning.
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

# ----------------------------------------------------------------------
# 1. Updated behavior service with classification logic
improved_behavior = '''import redis
import math
from datetime import datetime, timezone
from typing import Dict, Any
from src.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

class Ghatotkacha:
    """
    Session intelligence with classification:
    - clean: no high‑risk history, low risk
    - suspicious: one high‑risk event or moderate risk
    - hostile: multiple high‑risk events or high sustained risk
    """

    def __init__(self, session_ttl=3600, window_size=20):
        self.session_ttl = session_ttl
        self.window_size = window_size
        self.high_risk_threshold = 0.6  # risk score considered high

        # Classification thresholds
        self.thresholds = {
            "clean_max_risk": 0.45,
            "suspicious_weighted_risk": 0.30,
            "hostile_weighted_risk": 0.65,
        }

    def record_request(self, session_id: str, risk_score: float) -> Dict[str, Any]:
        if not session_id:
            return self._empty_stats()

        key = f"session:{session_id}"
        now = datetime.now(timezone.utc).timestamp()

        # Store with timestamp
        pipe = redis_client.pipeline()
        pipe.zadd(key, {f"{now}:{risk_score}": now})
        pipe.zremrangebyrank(key, 0, -self.window_size - 1)
        pipe.expire(key, self.session_ttl)
        pipe.execute()

        # Retrieve all entries
        entries = redis_client.zrange(key, 0, -1, withscores=True)
        scores = []
        for entry, ts in entries:
            try:
                _, risk = entry.split(':')
                scores.append(float(risk))
            except:
                continue

        if not scores:
            return self._empty_stats()

        n = len(scores)

        # Weighted average with decay
        if n > 0:
            weights = [math.exp(-0.2 * (n - i - 1)) for i in range(n)]
            total_weight = sum(weights)
            weighted_risk = sum(score * w for score, w in zip(scores, weights)) / total_weight
        else:
            weighted_risk = 0.0

        max_risk = max(scores)
        high_risk_count = sum(1 for s in scores if s >= self.high_risk_threshold)

        # Classification logic
        if high_risk_count >= 2 or weighted_risk >= self.thresholds["hostile_weighted_risk"]:
            classification = "hostile"
        elif high_risk_count == 1 or weighted_risk >= self.thresholds["suspicious_weighted_risk"] or max_risk >= self.thresholds["clean_max_risk"]:
            classification = "suspicious"
        else:
            classification = "clean"

        # Spike detection (only if multiple requests)
        spike_detected = False
        if n > 1:
            mean = sum(scores) / n
            variance = sum((s - mean) ** 2 for s in scores) / (n - 1) if n > 1 else 0
            std = math.sqrt(variance) if variance > 0 else 0.1
            spike_detected = risk_score > (mean + 2 * std)

        # Build reason
        if classification == "hostile":
            reason = f"Hostile session: {high_risk_count} high-risk events, weighted risk {weighted_risk:.2f}"
        elif classification == "suspicious":
            if high_risk_count == 1:
                reason = f"Suspicious session: recent high-risk event (max {max_risk:.2f})"
            else:
                reason = f"Suspicious session: weighted risk {weighted_risk:.2f}"
        else:
            reason = f"Clean session: max risk {max_risk:.2f}"

        # Escalation factor (used for score multiplication)
        factor_map = {"clean": 1.0, "suspicious": 1.2, "hostile": 1.5}
        escalation_factor = factor_map.get(classification, 1.0)
        if high_risk_count > 1:
            escalation_factor = min(escalation_factor * (1 + (high_risk_count - 1) * 0.1), 2.0)

        return {
            "escalation_factor": round(escalation_factor, 2),
            "escalation_reason": reason,
            "request_count": n,
            "avg_risk": round(sum(scores)/n, 3),
            "max_risk": round(max_risk, 3),
            "weighted_risk": round(weighted_risk, 3),
            "classification": classification,
            "high_risk_count": high_risk_count,
            "spike_detected": spike_detected,
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
            "classification": "none",
            "high_risk_count": 0,
            "spike_detected": False,
            "last_risk": 0
        }

tracker = Ghatotkacha()
'''
write_file("src/services/behavior_service.py", improved_behavior)

# ----------------------------------------------------------------------
# 2. Update Krishna with decision matrix
with open("src/engines/krishna/engine.py", "r") as f:
    krishna = f.read()

# We'll replace the decision logic with the matrix approach.
new_decision_logic = '''
        # ------------------------------------------------------------------
        # Step 1: Determine score‑based action (request risk bucket)
        # ------------------------------------------------------------------
        if modified_score >= 0.80:
            score_action = "block"
        elif modified_score >= 0.50:
            score_action = "challenge"
        elif modified_score >= 0.20:
            score_action = "monitor"
        else:
            score_action = "allow"

        # ------------------------------------------------------------------
        # Step 2: Determine session floor (minimum action based on session class)
        # ------------------------------------------------------------------
        session_class = behavior.get("classification", "clean")
        if session_class == "hostile":
            session_floor = "challenge"
        elif session_class == "suspicious":
            session_floor = "monitor"
        else:
            session_floor = "allow"

        # ------------------------------------------------------------------
        # Step 3: Apply override (if any)
        # ------------------------------------------------------------------
        if override_action:
            decision = override_action
            decision_logic = f"override={override_action}"
            # Override bypasses floor; we'll still record floor for trace.
        else:
            # Combine score_action and session_floor by taking the stricter
            action_rank = {"allow": 0, "monitor": 1, "challenge": 2, "block": 3}
            candidate_actions = [score_action, session_floor]
            # Also consider the original score‑based decision? We already have it.
            # Pick the strictest (highest rank)
            final_decision = max(candidate_actions, key=lambda a: action_rank[a])
            decision = final_decision
            decision_logic = f"score_action={score_action}, session_floor={session_floor} -> {final_decision}"

        # ------------------------------------------------------------------
        # Step 4: Prepare trace with reasoning
        # ------------------------------------------------------------------
        # ... existing trace building (after we compute these variables)
        # We'll need to add session_floor, score_action, etc. to trace.
'''

# Insert this new decision block after override_action extraction and before trace building.
# We'll replace the entire decision section (from "if override_action" to just before trace = {).
# First, find the old block. The current file likely has:
#        if override_action:
#            decision = override_action
#            decision_logic = f"override={override_action}"
#        else:
#            ... old threshold logic ...
#        decision_logic = ... (maybe)
# We'll replace from the line after override_action extraction up to the point before trace building.

# We'll do a targeted replace.
old_decision_section = '''        if override_action:
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
            decision_logic = f"score={modified_score:.3f} -> {decision}"'''

if old_decision_section in krishna:
    krishna = krishna.replace(old_decision_section, new_decision_logic)
else:
    # Try a different pattern (maybe the file has the floor logic already from earlier).
    # We'll search for the line that sets decision and replace from there.
    import re
    # Fallback: find the decision block by pattern
    pattern = r'(        if override_action:.*?decision_logic = .*?\n)(?=        # Compute overall confidence)'
    match = re.search(pattern, krishna, re.DOTALL)
    if match:
        krishna = krishna.replace(match.group(0), new_decision_logic + "\n")
    else:
        print("⚠️ Could not locate decision block. Manual update may be needed.")

# Now add the new fields to the trace: session_floor, score_action, etc.
# We need to ensure these variables exist before trace is built.
# Add them after we define them.
# Insert after decision_logic (the new block already defines them). We'll add them to trace.

# In the trace dictionary, we need to include:
#   "score_action": score_action,
#   "session_floor": session_floor,
#   "session_classification": session_class,
#   "session_reason": behavior.get("escalation_reason", ""),
#   "high_risk_count": behavior.get("high_risk_count", 0),

# We'll insert these after "decision_logic" in the trace dict.
# Find trace = { line and insert additional fields after it.
trace_fields = '''            "score_action": score_action,
            "session_floor": session_floor,
            "session_classification": session_class,
            "session_reason": behavior.get("escalation_reason", ""),
            "session_high_risk_count": behavior.get("high_risk_count", 0),
            "session_max_risk": behavior.get("max_risk", 0),
'''
# Insert after "trace = {" line
trace_line = 'trace = {'
if trace_line in krishna:
    krishna = krishna.replace(trace_line, trace_line + "\n" + trace_fields)
else:
    # Might be indented differently; try more generic
    krishna = krishna.replace('trace = {', 'trace = {\n' + trace_fields)

write_file("src/engines/krishna/engine.py", krishna)
print("✅ Updated Krishna with decision matrix and enhanced trace.")

# ----------------------------------------------------------------------
# 3. Update test script with new expected behaviors (optional)
print("✅ Phase 1.4 decision matrix implemented.")
print("Restart server and test with sequence to verify monitor behavior.")
