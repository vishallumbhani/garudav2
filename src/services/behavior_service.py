import redis
import math
from datetime import datetime, timezone
from typing import Dict, Any
from src.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

class Ghatotkacha:
    """
    Session intelligence with:
    - Weighted average with decay
    - Max risk tracking
    - High‑risk event count
    - Decision floors based on session state
    """

    def __init__(self, session_ttl=3600, window_size=20, high_risk_threshold=0.6):
        self.session_ttl = session_ttl
        self.window_size = window_size
        self.high_risk_threshold = high_risk_threshold

        # Classification thresholds (based on combined risk)
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

        # Store with timestamp
        try:
            # Store with timestamp
            pipe = redis_client.pipeline()
            pipe.zadd(key, {f"{now}:{risk_score}": now})
            pipe.zremrangebyrank(key, 0, -self.window_size - 1)
            pipe.expire(key, self.session_ttl)
            pipe.execute()

            # Retrieve all entries
            entries = redis_client.zrange(key, 0, -1, withscores=True)

        except Exception as e:
            return {
                "escalation_factor": 1.0,
                "escalation_reason": f"behavior engine degraded: {str(e)}",
                "request_count": 0,
                "avg_risk": 0,
                "max_risk": 0,
                "weighted_risk": 0,
                "combined_risk": 0,
                "classification": "degraded",
                "high_risk_count": 0,
                "spike_detected": False,
                "last_risk": risk_score,
                "engine_status": "degraded"
            }
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

        # Weighted average with exponential decay (recent more important)
        if n > 0:
            weights = [math.exp(-0.2 * (n - i - 1)) for i in range(n)]
            total_weight = sum(weights)
            weighted_risk = sum(score * w for score, w in zip(scores, weights)) / total_weight
        else:
            weighted_risk = 0.0

        max_risk = max(scores)
        high_risk_count = sum(1 for s in scores if s >= self.high_risk_threshold)

        # Combined risk: weighted average + max risk boost
        combined_risk = max(weighted_risk, max_risk * 0.8)

        # Classification based on combined risk
        classification = "clean"
        if combined_risk >= self.thresholds["compromised"]:
            classification = "compromised"
        elif combined_risk >= self.thresholds["malicious"]:
            classification = "malicious"
        elif combined_risk >= self.thresholds["suspicious"]:
            classification = "suspicious"

        # Spike detection: only if there is at least one previous request and current risk exceeds mean+2σ
        spike_detected = False
        if n > 1:
            mean = sum(scores) / n
            variance = sum((s - mean) ** 2 for s in scores) / (n - 1) if n > 1 else 0
            std = math.sqrt(variance) if variance > 0 else 0.1
            spike_detected = risk_score > (mean + 2 * std)

        # Build reason
        reason = f"Session {classification}"
        if max_risk >= self.high_risk_threshold:
            reason += f" (max risk {max_risk:.2f}, {high_risk_count} high-risk events)"
        else:
            reason += f" (weighted risk {weighted_risk:.2f})"

        # Escalation factor for score multiplication
        escalation_factor = {
            "clean": 1.0,
            "suspicious": 1.2,
            "malicious": 1.5,
            "compromised": 2.0
        }.get(classification, 1.0)

        # Additional boost for repeat offenses
        if high_risk_count > 1:
            repetition_boost = min(1 + (high_risk_count - 1) * 0.1, 1.5)
            escalation_factor *= repetition_boost

        escalation_factor = min(escalation_factor, 2.5)

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
            "combined_risk": 0,
            "classification": "clean",
            "high_risk_count": 0,
            "spike_detected": False,
            "last_risk": 0,
            "engine_status": "ok"
        }

tracker = Ghatotkacha()
