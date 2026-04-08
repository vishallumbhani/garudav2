"""
Decision aggregator with weighted scoring, policy modifier, behavior escalation,
deception labels, active override enforcement, and non-overridable guardrails.
"""

from typing import Dict, Any, Optional, List, Tuple
import psycopg2
from src.core.config import settings


class Krishna:
    def __init__(self):
        self.weights = {
            "bhishma": 0.5,
            "hanuman": 0.2,
            "shakuni": 0.15,
            "arjuna": 0.15,
        }
        self.trace_version = "1.3"
        self.db_url = settings.DATABASE_URL.replace("+asyncpg", "")

    def _resolve_tenant_uuid(self, tenant_key: Optional[str]) -> Optional[str]:
        if not tenant_key:
            return None

        conn = psycopg2.connect(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM tenants WHERE tenant_key = %s", (tenant_key,))
                row = cur.fetchone()
                if not row:
                    return None
                return str(row[0])
        finally:
            conn.close()

    def _get_active_override(self, tenant_key: Optional[str], target_refs: List[str]) -> Optional[Dict[str, Any]]:
        if not tenant_key or not target_refs:
            return None

        tenant_id = self._resolve_tenant_uuid(tenant_key)
        if not tenant_id:
            return None

        conn = psycopg2.connect(self.db_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, override_type, target_ref, reason, status, expires_at, created_at
                    FROM override_events
                    WHERE tenant_id = %s
                      AND status = 'active'
                      AND (expires_at IS NULL OR expires_at > NOW())
                      AND target_ref = ANY(%s)
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (tenant_id, target_refs),
                )
                row = cur.fetchone()
                if not row:
                    return None

                return {
                    "id": str(row[0]),
                    "override_type": row[1],
                    "target_ref": row[2],
                    "reason": row[3],
                    "status": row[4],
                    "expires_at": row[5].isoformat() if row[5] else None,
                    "created_at": row[6].isoformat() if row[6] else None,
                }
        finally:
            conn.close()

    def _build_override_targets(
        self,
        request,
        policy_reason_codes: List[str],
        secret_severity: Optional[str],
        sensitivity_label: str,
    ) -> List[str]:
        targets: List[str] = []

        endpoint = "scan:file" if getattr(request, "content_type", None) == "file" else "scan:text"
        targets.append(endpoint)

        for code in policy_reason_codes or []:
            if code.startswith("POLICY_"):
                policy_key = code.replace("POLICY_", "").lower()
                targets.append(f"policy:{policy_key}")

        # compatibility for your current test naming
        if "POLICY_BLOCK_PRIVATE_KEYS" in (policy_reason_codes or []):
            targets.append("policy:block_private_keys")

        if secret_severity:
            targets.append(f"secret:{str(secret_severity).lower()}")

        if sensitivity_label:
            targets.append(f"sensitivity:{str(sensitivity_label).upper()}")

        seen = set()
        deduped = []
        for t in targets:
            if t not in seen:
                deduped.append(t)
                seen.add(t)
        return deduped

    def _apply_active_override(
        self,
        decision: str,
        decision_logic: str,
        active_override: Optional[Dict[str, Any]],
        non_overridable_guardrail: bool,
        effective_override_scope: str,
        hard_stop_reasons: List[str],
    ) -> Tuple[str, str, bool, bool, Optional[str]]:
        """
        Returns:
        - decision
        - decision_logic
        - override_applied
        - override_denied
        - override_denial_reason
        """
        if not active_override:
            return decision, decision_logic, False, False, None

        override_type = active_override.get("override_type")
        override_target = active_override.get("target_ref")

        if non_overridable_guardrail:
            denial_reason = "non-overridable guardrail"
            if hard_stop_reasons:
                denial_reason += f" ({', '.join(hard_stop_reasons)})"
            decision_logic += f" (active override denied: {denial_reason})"
            return decision, decision_logic, False, True, denial_reason

        if effective_override_scope == "none":
            denial_reason = "override_scope=none"
            decision_logic += f" (active override denied: {denial_reason})"
            return decision, decision_logic, False, True, denial_reason

        if effective_override_scope == "challenge_only":
            if decision == "block":
                decision = "challenge"
                decision_logic += f" (active override: {override_type} on {override_target} -> challenge)"
                return decision, decision_logic, True, False, None
            return decision, decision_logic, False, False, None

        if effective_override_scope == "allow":
            if override_type in ["break_glass", "temporary_allow", "retrieval_unblock"]:
                if decision != "allow":
                    decision = "allow"
                    decision_logic += f" (active override: {override_type} on {override_target} -> allow)"
                return decision, decision_logic, True, False, None

        return decision, decision_logic, False, False, None

    def run(self, request, engine_results: Dict[str, Any]) -> Dict[str, Any]:
        bhishma = engine_results.get("bhishma", {}) or {}
        hanuman = engine_results.get("hanuman", {}) or {}
        yudhishthira = engine_results.get("yudhishthira", {}) or {}
        policy_action = yudhishthira.get("policy_action")
        policy_reason_codes = yudhishthira.get("reason_codes", [])
        non_overridable_match = yudhishthira.get("non_overridable_match", False)
        effective_override_scope = yudhishthira.get("effective_override_scope", "allow")
        global_guardrail_hit = yudhishthira.get("global_guardrail_hit", False)

        behavior = engine_results.get("behavior", {}) or {}
        shakuni = engine_results.get("shakuni", {}) or {}
        arjuna = engine_results.get("arjuna", {}) or {}
        threat_memory = engine_results.get("threat_memory", {}) or {}
        kautilya_info = engine_results.get("kautilya", {}) or {}
        classification = engine_results.get("data_classification", {}) or {}

        pii_detected = classification.get("pii_detected", False)
        pii_types = classification.get("pii_types", [])
        finance_detected = classification.get("finance_detected", False)
        finance_types = classification.get("finance_types", [])
        credential_detected = classification.get("credential_detected", False)
        trade_secret_detected = classification.get("trade_secret_detected", False)
        phi_detected = classification.get("phi_detected", False)
        classification_reason = classification.get("classification_reason", "") or {}

        hanuman_info = hanuman
        hanuman_content_kind = hanuman_info.get("content_kind", "unknown")
        hanuman_risk_hint = hanuman_info.get("risk_hint", "unknown")
        hanuman_complexity = hanuman_info.get("complexity", "unknown")
        hanuman_likely_family = hanuman_info.get("likely_family", "unknown")
        hanuman_language_hint = hanuman_info.get("language_hint", "")
        hanuman_log_type_hint = hanuman_info.get("log_type_hint", "")
        hanuman_document_type_hint = hanuman_info.get("document_type_hint", "")
        hanuman_line_count = hanuman_info.get("line_count", 0)
        hanuman_section_count = hanuman_info.get("section_count", 0)
        hanuman_has_code_blocks = hanuman_info.get("has_code_blocks", False)
        hanuman_has_stack_trace = hanuman_info.get("has_stack_trace", False)
        hanuman_has_secrets_pattern = hanuman_info.get("has_secrets_pattern", False)
        hanuman_summary = hanuman_info.get("summary", {}) or {}
        hanuman_detected_secrets = hanuman_info.get("detected_secrets", [])
        secret_severity = hanuman_info.get("secret_severity")
        hanuman_detected_dangerous = hanuman_info.get("detected_dangerous_functions", [])
        hanuman_code_risk_hint = hanuman_info.get("code_risk_hint")
        hanuman_code_risk_reason = hanuman_info.get("code_risk_reason")

        bhishma_score = bhishma.get("score", 0.5)
        hanuman_score = hanuman.get("score", 0.5)
        shakuni_score = shakuni.get("score", 0.5)
        arjuna_score = arjuna.get("score", 0.5)

        base_weighted = (
            self.weights["bhishma"] * bhishma_score
            + self.weights["hanuman"] * hanuman_score
            + self.weights["shakuni"] * shakuni_score
            + self.weights["arjuna"] * arjuna_score
        )

        policy_modifier = yudhishthira.get("modifier", 1.0)
        behavior_modifier = behavior.get("escalation_factor", 1.0)
        behavior_reason = behavior.get("escalation_reason", "no data")
        threat_session_modifier = threat_memory.get("session_modifier", 1.0)
        threat_global_modifier = threat_memory.get("global_modifier", 1.0)

        modified_score = (
            base_weighted
            * policy_modifier
            * behavior_modifier
            * threat_session_modifier
            * threat_global_modifier
        )
        modified_score = min(modified_score, 0.95)

        override_action = yudhishthira.get("override_action")
        override_reason = yudhishthira.get("override_reason")

        if modified_score >= 0.80:
            score_action = "block"
        elif modified_score >= 0.50:
            score_action = "challenge"
        elif modified_score >= 0.20:
            score_action = "monitor"
        else:
            score_action = "allow"

        session_class = behavior.get("classification", "clean")
        if session_class == "hostile":
            session_floor = "challenge"
        elif session_class == "suspicious":
            session_floor = "monitor"
        else:
            session_floor = "allow"

        action_rank = {"allow": 0, "monitor": 1, "challenge": 2, "block": 3}

        if override_action:
            decision = override_action
            decision_logic = f"override={override_action}"
        else:
            candidate_actions = [score_action, session_floor]
            final_decision = max(candidate_actions, key=lambda a: action_rank.get(a, 0))
            decision = final_decision
            decision_logic = f"score_action={score_action}, session_floor={session_floor} -> {final_decision}"

        arjuna_label = arjuna.get("label", "")
        arjuna_conf = arjuna.get("confidence", 0.0)
        shakuni_labels = shakuni.get("labels", [])
        category_floor = "allow"

        if arjuna_label == "data_exfiltration" and arjuna_conf >= 0.80:
            category_floor = "challenge"
        if arjuna_label == "policy_bypass" and arjuna_conf >= 0.85:
            category_floor = "challenge"
        if "indirect_bypass_phrasing" in shakuni_labels or "hypothetical_justification" in shakuni_labels:
            category_floor = "challenge"

        high_intent_labels = [
            "covert_exfiltration_intent",
            "covert_transfer_intent",
            "authentication_bypass_intent",
            "secret_extraction_intent",
            "data_theft_intent",
        ]
        for label in shakuni_labels:
            if label == "authentication_bypass_intent":
                category_floor = "block"
                break
            if label in high_intent_labels:
                category_floor = "challenge"
                break

        if action_rank.get(decision, 0) < action_rank.get(category_floor, 0):
            decision = category_floor
            decision_logic += f" (category floor: {category_floor})"

        if policy_action == "block":
            decision = "block"
            decision_logic += f" (policy_action={policy_action} -> block)"
        elif policy_action == "challenge" and decision != "block":
            decision = "challenge"
            decision_logic += f" (policy_action={policy_action} -> challenge)"
        elif policy_action == "monitor" and decision not in ["block", "challenge"]:
            decision = "monitor"
            decision_logic += f" (policy_action={policy_action} -> monitor)"

        sensitivity_label = classification.get("sensitivity_label", "LOW")

        if sensitivity_label == "CRITICAL":
            decision = "block"
            decision_logic += " (sensitivity: CRITICAL -> block)"
        elif sensitivity_label == "HIGH" and decision != "block":
            decision = "challenge"
            decision_logic += " (sensitivity: HIGH -> challenge)"
        elif sensitivity_label == "MEDIUM" and decision not in ["block", "challenge"]:
            decision = "monitor"
            decision_logic += " (sensitivity: MEDIUM -> monitor)"

        if secret_severity == "critical":
            decision = "block"
            decision_logic += " (secret severity: critical -> block)"
        elif secret_severity == "high" and decision != "block":
            decision = "challenge"
            decision_logic += " (secret severity: high -> challenge)"

        # Non-overridable runtime hard stops
        hard_stop_reasons = []
        if secret_severity == "critical":
            hard_stop_reasons.append("critical_secret")
        if global_guardrail_hit:
            hard_stop_reasons.append("global_guardrail")
        if non_overridable_match:
            hard_stop_reasons.append("non_overridable_policy")

        non_overridable_guardrail = len(hard_stop_reasons) > 0

        # Active override lookup and application
        target_refs = self._build_override_targets(
            request=request,
            policy_reason_codes=policy_reason_codes,
            secret_severity=secret_severity,
            sensitivity_label=sensitivity_label,
        )
        active_override = self._get_active_override(
            tenant_key=getattr(request, "tenant_id", None),
            target_refs=target_refs,
        )
        decision, decision_logic, override_applied, override_denied, override_denial_reason = self._apply_active_override(
            decision=decision,
            decision_logic=decision_logic,
            active_override=active_override,
            non_overridable_guardrail=non_overridable_guardrail,
            effective_override_scope=effective_override_scope,
            hard_stop_reasons=hard_stop_reasons,
        )

        bhishma_conf = bhishma.get("confidence", 0.7)
        hanuman_conf = hanuman.get("confidence", 0.8)
        shakuni_conf = shakuni.get("confidence", 0.7)

        if override_action:
            confidence = 0.95
        else:
            confidence = (
                self.weights["bhishma"] * bhishma_conf
                + self.weights["hanuman"] * hanuman_conf
                + self.weights["shakuni"] * shakuni_conf
            )
            confidence = confidence * (1 / max(1.0, policy_modifier)) * (1 / max(1.0, behavior_modifier))
            confidence = min(confidence, 0.95)

        confidence = round(confidence, 3)

        degraded_engines = [
            name for name, r in engine_results.items()
            if isinstance(r, dict) and r.get("status") == "degraded"
        ]
        fallback_used = len(degraded_engines) > 0
        status = "degraded" if fallback_used else "ok"

        endpoint = "scan:file" if getattr(request, "content_type", None) == "file" else "scan:text"

        trace = {
            "endpoint": endpoint,
            "score_action": score_action,
            "session_floor": session_floor,
            "session_classification": session_class,
            "session_reason": behavior.get("escalation_reason", ""),
            "session_high_risk_count": behavior.get("high_risk_count", 0),
            "session_max_risk": behavior.get("max_risk", 0),
            "threat_session_modifier": round(threat_session_modifier, 2),
            "threat_global_modifier": round(threat_global_modifier, 2),
            "trace_version": self.trace_version,
            "status": status,
            "fallback_used": fallback_used,
            "degraded_engines": degraded_engines,
            "confidence": confidence,
            "deception_labels": shakuni_labels,
            "arjuna_label": arjuna_label,
            "arjuna_confidence": arjuna_conf,
            "arjuna_reason": arjuna.get("reason", ""),
            "hanuman_content_kind": hanuman_content_kind,
            "hanuman_risk_hint": hanuman_risk_hint,
            "hanuman_complexity": hanuman_complexity,
            "hanuman_likely_family": hanuman_likely_family,
            "hanuman_language_hint": hanuman_language_hint,
            "hanuman_log_type_hint": hanuman_log_type_hint,
            "hanuman_document_type_hint": hanuman_document_type_hint,
            "hanuman_line_count": hanuman_line_count,
            "hanuman_section_count": hanuman_section_count,
            "hanuman_has_code_blocks": hanuman_has_code_blocks,
            "hanuman_has_stack_trace": hanuman_has_stack_trace,
            "hanuman_has_secrets_pattern": hanuman_has_secrets_pattern,
            "hanuman_summary_chunk_count": hanuman_summary.get("chunk_count", 0),
            "hanuman_summary_suspicious_phrases": hanuman_summary.get("suspicious_phrases", []),
            "hanuman_summary_top_keywords": hanuman_summary.get("top_keywords", []),
            "hanuman_detected_secrets": hanuman_detected_secrets,
            "secret_severity": secret_severity,
            "hanuman_detected_dangerous_functions": hanuman_detected_dangerous,
            "hanuman_code_risk_hint": hanuman_code_risk_hint,
            "hanuman_code_risk_reason": hanuman_code_risk_reason,
            "kautilya_path": kautilya_info.get("path"),
            "kautilya_reason": kautilya_info.get("reason"),
            "kautilya_engines_run": kautilya_info.get("engines_run", []),
            "kautilya_engines_skipped": kautilya_info.get("engines_skipped", []),
            "kautilya_cost_tier": kautilya_info.get("cost_tier"),
            "kautilya_latency_budget_ms": kautilya_info.get("latency_budget_ms"),
            "sensitivity_label": sensitivity_label,
            "pii_detected": pii_detected,
            "pii_types": pii_types,
            "finance_detected": finance_detected,
            "finance_types": finance_types,
            "credential_detected": credential_detected,
            "trade_secret_detected": trade_secret_detected,
            "phi_detected": phi_detected,
            "classification_reason": classification_reason,
            "data_categories": classification.get("data_categories", []),
            "weights": self.weights,
            "scores": {
                "bhishma": round(bhishma_score, 3),
                "hanuman": round(hanuman_score, 3),
                "shakuni": round(shakuni_score, 3),
                "arjuna": round(arjuna_score, 3),
            },
            "base_weighted_score": round(base_weighted, 3),
            "policy_modifier": round(policy_modifier, 2),
            "behavior_modifier": round(behavior_modifier, 2),
            "behavior_reason": behavior_reason,
            "modified_score": round(modified_score, 3),
            "decision_logic": decision_logic,
            "policy_action": policy_action,
            "policy_reason_codes": policy_reason_codes,
            "matched_policy_meta": yudhishthira.get("matched_policy_meta", []),
            "non_overridable_match": non_overridable_match,
            "effective_override_scope": effective_override_scope,
            "global_guardrail_hit": global_guardrail_hit,
            "hard_stop_reasons": hard_stop_reasons,
            "active_override": active_override,
            "override_applied": override_applied,
            "override_denied": override_denied,
            "override_denial_reason": override_denial_reason,
            "override_target_refs_checked": target_refs,
        }

        if override_action:
            trace["override"] = override_action
            trace["override_reason"] = override_reason

        if active_override:
            trace["runtime_override_type"] = active_override.get("override_type")
            trace["runtime_override_target_ref"] = active_override.get("target_ref")
            trace["runtime_override_reason"] = active_override.get("reason")

        if hasattr(request, "file_metadata") and request.file_metadata:
            trace["file_metadata"] = request.file_metadata

        external_score = int(round(modified_score * 100))

        return {
            "engine": "krishna",
            "score": external_score,
            "normalized_score": round(modified_score, 3),
            "decision": decision,
            "details": {"trace": trace},
        }