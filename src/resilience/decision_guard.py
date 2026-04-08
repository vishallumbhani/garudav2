import logging
from typing import List, Optional, Dict, Any
from src.core.fallback import fallback

logger = logging.getLogger(__name__)

class DecisionGuard:
    """Constrains final decision based on system trust level."""

    def __init__(self):
        self.integrity_failures: List[str] = []
        self.critical_engines = {"arjuna", "bhishma", "shakuni"}

    def evaluate(
        self,
        decision: str,
        score: float = 0,
        integrity_result: Optional[Dict[str, Any]] = None,
        resilience_state: Optional[Dict[str, Any]] = None,
        engine_results: Optional[Dict[str, Any]] = None,
        request: Optional[Any] = None,
    ) -> str:
        """
        Apply guard logic with full context.
        Parameters:
            decision: base decision (allow, monitor, challenge, block)
            score: numerical score
            integrity_result, resilience_state, engine_results, request: optional context
        """
        # 1. Integrity failures (most severe)
        if fallback.integrity_failures:
            logger.critical("Integrity failures present - forcing block")
            return "block"

        if integrity_result and integrity_result.get("status") == "failed":
            logger.critical("Integrity precheck failed - forcing block")
            return "block"

        # 2. Safe mode (explicit flag, can be set externally)
        if resilience_state and resilience_state.get("safe_mode"):
            logger.warning("Safe mode from resilience state active")
            return "challenge" if decision == "allow" else decision
        # 3. Degraded engines impact
        degraded_engines = list(fallback.degraded_engines)
        if resilience_state and "degraded_engines" in resilience_state:
            degraded_engines = resilience_state.get("degraded_engines", [])

        degraded_critical = [e for e in degraded_engines if e in self.critical_engines]
        if len(degraded_critical) >= 2:
            logger.warning(f"Multiple critical engines degraded {degraded_critical} - forcing challenge")
            return "challenge"
        elif degraded_critical:
            if decision == "allow":
                return "monitor"

        # 4. High score with any degradation
        if score >= 0.8 and degraded_engines:
            return "block"

        return decision


def check_multi_engine_degradation(degraded_engines, threshold=2):
    """Activate safe mode if multiple critical engines are degraded."""
    from src.core.fallback import fallback
    critical = {"arjuna", "bhishma", "shakuni"}
    degraded_critical = [e for e in degraded_engines if e in critical]
    if len(degraded_critical) >= threshold:
        fallback.enable_safe_mode(f"{len(degraded_critical)} critical engines degraded")
        return True
    return False


decision_guard = DecisionGuard()
