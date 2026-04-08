import logging
logger = logging.getLogger(__name__)
import asyncio
from pathlib import Path
from src.core.models import ScanRequest, ScanResponse
from src.utils.file_extractors_v2 import extract_file as extract_from_file
from src.engines.hanuman.engine import Hanuman
from src.engines.bhishma.engine import Bhishma
from src.engines.shakuni.engine import Shakuni
from src.engines.arjuna.engine import Arjuna
from src.engines.classification.engine import DataClassification
from src.engines.yudhishthira.engine import Yudhishthira
from src.engines.krishna.engine import Krishna
from src.engines.sanjaya.engine import Sanjaya
from src.services.audit_service import log_audit
from src.services.behavior_service import tracker
from src.services.threat_memory import threat_memory
from src.services.kautilya import kautilya
from src.core.fallback import fallback
from src.resilience.decision_guard import decision_guard
from src.db.base import AsyncSessionLocal

# Phase 5 playbooks
from src.playbooks.throttle import is_throttled
from src.playbooks.isolation import is_session_isolated, isolate_session
from src.playbooks.alerting import send_alert
from src.playbooks.severity import map_decision_to_severity, Severity
from src.playbooks.quarantine import quarantine_file


async def _apply_playbooks(session_id: str, decision: str, score: float,
                           file_path: str = None, resilience_state: dict = None,
                           integrity_result: dict = None) -> dict:
    """Apply playbooks and return structured actions."""
    has_failures = resilience_state.get("fallback_used", False) if resilience_state else False
    severity = map_decision_to_severity(decision, has_failures, is_session_isolated(session_id))
    actions = {
        "severity": int(severity),
        "alert_sent": False,
        "quarantined": False,
        "isolated": False,
        "throttled": False,
        "actions": []
    }

    if severity <= Severity.HIGH:
        send_alert(
            severity=int(severity),
            title=f"Scan decision: {decision}",
            description=f"Session {session_id} triggered {decision}",
            context={"score": score, "decision": decision, "engines_degraded": resilience_state.get("degraded_engines", [])}
        )
        actions["alert_sent"] = True
        actions["actions"].append("alert")

    if file_path and decision in ("block", "challenge") and Path(file_path).exists():
        quarantine_file(Path(file_path), reason=f"Scan decision: {decision}")
        actions["quarantined"] = True
        actions["actions"].append("quarantine")

    if decision == "block" and resilience_state and resilience_state.get("critical_engine_failures", 0) >= 2:
        isolate_session(session_id, reason="Repeated blocks with engine failures")
        actions["isolated"] = True
        actions["actions"].append("isolate")

    return actions


async def scan_text(request: ScanRequest) -> ScanResponse:
    request.normalized_text = request.content if isinstance(request.content, str) else request.content.decode('utf-8', errors='ignore')
    return await _run_pipeline(request)


async def scan_file(request: ScanRequest) -> ScanResponse:
    temp_file = Path("/tmp") / f"garuda_{request.event_id}.tmp"
    temp_file.write_bytes(request.content)
    try:
        extraction = extract_from_file(temp_file, request.filename or "unknown")
        if not extraction.get("success", False):
            from fastapi import HTTPException
            metadata = extraction.get("metadata", {}) or {}
            if metadata.get("blocked") and metadata.get("reason") == "unsupported_file_type":
                raise HTTPException(status_code=415, detail=extraction.get("error", "Unsupported file type"))
            raise HTTPException(status_code=422, detail=extraction.get("error", "File extraction failed"))
        request.normalized_text = extraction["text"]
        request.file_metadata = extraction["metadata"]
        request.normalized_chunks = extraction.get("chunks", [])
        request._temp_file_path = temp_file
    except Exception:
        temp_file.unlink(missing_ok=True)
        raise
    return await _run_pipeline(request)


async def _run_pipeline(request) -> ScanResponse:

    # Reset per-request fallback state to avoid stale global state
    fallback.safe_mode = False
    fallback.degraded_engines = set()
    fallback.integrity_failures = []
    # ========== 1. SESSION CONTROLS ==========
    if request.session_id:
        if is_session_isolated(request.session_id):
            return ScanResponse(
                decision="block",
                score=1.0,
                reason="Session isolated due to prior hostile activity",
                normalized_score=1.0
            )
        throttled, _ = is_throttled(request.session_id)
        if throttled:
            return ScanResponse(
                decision="throttle",
                score=0.5,
                reason="Rate limit exceeded",
                normalized_score=0.5
            )

    # ========== 2. INTEGRITY PRECHECK ==========
    from src.protection.integrity import run_integrity_precheck
    integrity_result = run_integrity_precheck(request)

    # ========== 3. HEALTH PRECHECK ==========
    from src.resilience.health import get_runtime_health_snapshot
    health_result = get_runtime_health_snapshot()

    # ========== 4. ENGINE EXECUTION ==========
    engine_results = {}

    hanuman_result = fallback.wrap_engine("hanuman", lambda req: Hanuman().run(req), request)
    engine_results["hanuman"] = hanuman_result

    bhishma_result = fallback.wrap_engine("bhishma", lambda req, hr: Bhishma().run(req, hr), request, hanuman_result)
    engine_results["bhishma"] = bhishma_result

    if request.session_id:
        risk_score = bhishma_result.get("score", 0.5)
        stats = tracker.record_request(request.session_id, risk_score)
        behavior_result = {
            "engine": "behavior",
            "status": "degraded" if stats.get("engine_status") == "degraded" else "ok",
            "escalation_factor": stats["escalation_factor"],
            "escalation_reason": stats["escalation_reason"],
            "request_count": stats["request_count"],
            "high_risk_count": stats["high_risk_count"],
            "avg_risk": stats["avg_risk"],
            "max_risk": stats["max_risk"],
            "weighted_risk": stats["weighted_risk"],
            "combined_risk": stats.get("combined_risk", 0),
            "classification": stats["classification"],
            "spike_detected": stats["spike_detected"],
            "last_risk": stats["last_risk"],
        }
    else:
        behavior_result = {
            "engine": "behavior",
            "status": "ok",
            "escalation_factor": 1.0,
            "escalation_reason": "no session",
            "classification": "none",
            "request_count": 0,
            "high_risk_count": 0,
            "avg_risk": 0,
            "max_risk": 0,
            "weighted_risk": 0,
            "combined_risk": 0,
            "spike_detected": False,
            "last_risk": 0,
        }
    engine_results["behavior"] = behavior_result

    if request.session_id:
        if request.content_type == "text":
            threat_result = fallback.wrap_engine(
                "threat_memory",
                lambda sid, text: threat_memory.get_memory_modifiers(sid, text),
                request.session_id,
                request.normalized_text,
            )
        else:
            threat_result = fallback.wrap_engine(
                "threat_memory",
                lambda sid, text, content: threat_memory.get_memory_modifiers(sid, text, content),
                request.session_id,
                request.normalized_text,
                request.content,
            )
        engine_results["threat_memory"] = threat_result
    else:
        engine_results["threat_memory"] = {
            "engine": "threat_memory",
            "status": "ok",
            "engine_status": "ok",
            "session_modifier": 1.0,
            "session_reason": "No session",
            "global_modifier": 1.0,
            "global_reason": "No session",
        }

    session_class = behavior_result.get("classification", "clean")
    bhishma_score = bhishma_result.get("score", 0.5)
    hanuman_score = hanuman_result.get("score", 0.5)
    threat_session_modifier = engine_results["threat_memory"].get("session_modifier", 1.0)
    threat_global_modifier = engine_results["threat_memory"].get("global_modifier", 1.0)
    file_present = (request.content_type == "file")
    tenant_strict_mode = False

    routing = kautilya.select_path(
        request, session_class, bhishma_score, hanuman_score,
        threat_session_modifier, threat_global_modifier,
        file_present, tenant_strict_mode
    )
    engine_policy = kautilya.get_engine_policy(routing["path_selected"])
    engine_results["kautilya"] = {
        "engine": "kautilya",
        "status": "ok",
        "path": routing["path_selected"],
        "reason": routing["path_reason"],
        "engines_run": routing["engines_run"],
        "engines_skipped": routing["engines_skipped"],
        "cost_tier": routing["cost_tier"],
        "latency_budget_ms": routing["latency_budget_ms"],
    }

    if engine_policy.get("shakuni", True):
        shakuni_result = fallback.wrap_engine("shakuni", Shakuni().run, request)
        engine_results["shakuni"] = shakuni_result
    else:
        engine_results["shakuni"] = {"engine": "shakuni", "status": "skipped", "score": 0.0}

    if engine_policy.get("arjuna", True):
        arjuna_result = fallback.wrap_engine("arjuna", Arjuna().run, request)
        engine_results["arjuna"] = arjuna_result
    else:
        engine_results["arjuna"] = {"engine": "arjuna", "status": "skipped", "score": 0.0}

    # Record threat memory only for suspicious content
    if request.session_id:
        try:
            should_record_threat = (
                bhishma_result.get("score", 0) >= 0.35
                or hanuman_result.get("risk_hint") == "high"
                or hanuman_result.get("secret_severity") in {"high", "critical"}
                or len(shakuni_result.get("labels", [])) >= 2
                or arjuna_result.get("confidence", 0) >= 0.75
            )

            if should_record_threat:
                threat_memory.record_prompt(request.session_id, request.normalized_text)
                if request.content_type == "file":
                    threat_memory.record_file(request.session_id, request.content)
        except Exception:
            pass

    classification_result = fallback.wrap_engine("data_classification", DataClassification().run, request)
    engine_results["data_classification"] = classification_result

    policy_context = {
        "tenant_id": request.tenant_id,
        "endpoint": "scan:text" if request.content_type == "text" else "scan:file",
        "data_categories": classification_result.get("data_categories", []),
        "sensitivity_label": classification_result.get("sensitivity_label", "LOW"),
        "secret_severity": (
            hanuman_result.get("secret_severity")
            or classification_result.get("secret_severity")
        ),
    }

    if engine_policy.get("yudhishthira", True):
        yudhishthira_result = fallback.wrap_engine(
            "yudhishthira",
            lambda req, bhr, ctx: Yudhishthira().run(req, bhr, ctx),
            request,
            bhishma_result,
            policy_context,
        )
        engine_results["yudhishthira"] = yudhishthira_result
    else:
        engine_results["yudhishthira"] = {"engine": "yudhishthira", "status": "skipped", "modifier": 1.0}

    krishna_result = fallback.wrap_engine("krishna", Krishna().run, request, engine_results)
    engine_results["krishna"] = krishna_result

    sanjaya = Sanjaya()
    response = sanjaya.run(request, krishna_result)

    # ========== 5. RESILIENCE STATE ==========
    degraded_engines = list(fallback.degraded_engines)
    critical_engines = {"hanuman", "bhishma", "arjuna", "krishna", "sanjaya"}
    critical_failures = [e for e in degraded_engines if e in critical_engines]
    resilience_state = {
        "status": "degraded" if degraded_engines else "ok",
        "fallback_used": bool(degraded_engines),
        "degraded_engines": degraded_engines,
        "critical_engine_failures": len(critical_failures),
        "safe_mode": False,
        "safe_mode_reason": None,
    }

    # ========== 6. SAFE MODE EVALUATION ==========
    from src.resilience.safe_mode import evaluate_safe_mode
    safe_mode_result = evaluate_safe_mode(integrity_result, resilience_state)
    resilience_state["safe_mode"] = safe_mode_result["active"]
    resilience_state["safe_mode_reason"] = safe_mode_result["reason"]

    if safe_mode_result["active"]:
        fallback.enable_safe_mode(safe_mode_result["reason"])
    else:
        fallback.safe_mode = False

    # ========== 7. BASE DECISION ==========
    # Already set as response

    # ========== 8. DECISION GUARD ==========
    original_decision = response.decision
    guarded_decision = decision_guard.evaluate(
        decision=original_decision,
        score=response.score,
        integrity_result=integrity_result,
        resilience_state=resilience_state,
        engine_results=engine_results,
        request=request,
    )
    if guarded_decision != original_decision:
        logger.warning(f"Decision overridden: {original_decision} -> {guarded_decision} due to degraded trust")
        response.decision = guarded_decision

    # ========== 9. POLICY FINALIZATION (implicit) ==========

    # ========== 10. PLAYBOOKS ==========
    temp_path = getattr(request, '_temp_file_path', None)
    playbook_actions = await _apply_playbooks(
        session_id=request.session_id,
        decision=response.decision,
        score=response.score,
        file_path=str(temp_path) if temp_path and temp_path.exists() else None,
        resilience_state=resilience_state,
        integrity_result=integrity_result,
    )
    if temp_path and temp_path.exists():
        temp_path.unlink(missing_ok=True)

    # ========== 11. AUDIT ==========
    trace = krishna_result.get("details", {}).get("trace", {}) or {}
    yudhishthira_result = engine_results.get("yudhishthira", {}) or {}
    audit_data = {
        "event_id": request.event_id,
        "tenant_id": request.tenant_id,
        "user_id": request.user_id,
        "session_id": request.session_id,
        "input_type": request.content_type,
        "endpoint": "scan:text" if request.content_type == "text" else "scan:file",
        "decision": response.decision,
        "final_score": response.score,
        "normalized_score": response.normalized_score,
        "policy_action": yudhishthira_result.get("policy_action") or trace.get("policy_action"),
        "policy_reason_codes": yudhishthira_result.get("reason_codes") or trace.get("policy_reason_codes", []),
        "override_applied": bool(trace.get("override_applied")),
        "engine_results": engine_results,
        "trace": trace,
        "playbook_actions": playbook_actions,
        "resilience_state": resilience_state,
        "integrity_status": integrity_result["status"],
        "health_status": health_result["status"],
    }
    async with AsyncSessionLocal() as db:
        await log_audit(audit_data)

    return response
