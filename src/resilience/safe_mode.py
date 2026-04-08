import logging
logger = logging.getLogger(__name__)

def evaluate_safe_mode(integrity_result, resilience_state):
    """Determine if safe mode should be active."""
    active = False
    reason = None
    if integrity_result.get("safe_mode_required"):
        active = True
        reason = "integrity check failed"
    elif resilience_state.get("critical_engine_failures", 0) >= 2:
        active = True
        reason = f"multiple critical engines degraded: {resilience_state.get('degraded_engines', [])}"
    elif resilience_state.get("fallback_used") and resilience_state.get("status") == "degraded":
        # Optional: less strict
        pass
    return {"active": active, "reason": reason}