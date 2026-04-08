from pathlib import Path

path = Path("src/engines/krishna/engine.py")

full_krishna = '''"""
Decision aggregator with weighted scoring, policy modifier, behavior escalation, and deception labels.
"""

from typing import Dict, Any

class Krishna:
    def __init__(self):
        self.weights = {"bhishma": 0.5, "hanuman": 0.2, "shakuni": 0.15, "arjuna": 0.15}
        self.trace_version = "1.1"

    def run(self, request, engine_results: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Extract all engine results safely
            bhishma = engine_results.get("bhishma") or {}
            hanuman = engine_results.get("hanuman") or {}
            shakuni = engine_results.get("shakuni") or {}
            arjuna = engine_results.get("arjuna") or {}
            yudhishthira = engine_results.get("yudhishthira") or {}
            behavior = engine_results.get("behavior") or {}
            threat_memory = engine_results.get("threat_memory") or {}
            kautilya_info = engine_results.get("kautilya") or {}
            classification = engine_results.get("data_classification") or {}

            # Extract scores
            bhishma_score = bhishma.get("score", 0.5)
            hanuman_score = hanuman.get("score", 0.5)
            shakuni_score = shakuni.get("score", 0.5)
            arjuna_score = arjuna.get("score", 0.5)

            # Weighted base score
            base_weighted = (self.weights["bhishma"] * bhishma_score +
                             self.weights["hanuman"] * hanuman_score +
                             self.weights["shakuni"] * shakuni_score +
                             self.weights["arjuna"] * arjuna_score)

            policy_modifier = yudhishthira.get("modifier", 1.0)
            behavior_modifier = behavior.get("escalation_factor", 1.0)
            behavior_reason = behavior.get("escalation_reason", "no data")
            threat_session_modifier = threat_memory.get("session_modifier", 1.0)
            threat_global_modifier = threat_memory.get("global_modifier", 1.0)

            modified_score = base_weighted * policy_modifier * behavior_modifier * threat_session_modifier * threat_global_modifier
            modified_score = min(modified_score, 0.95)

            override_action = yudhishthira.get("override_action")
            override_reason = yudhishthira.get("override_reason")

            # Score-based action
            if modified_score >= 0.80:
                score_action = "block"
            elif modified_score >= 0.50:
                score_action = "challenge"
            elif modified_score >= 0.20:
                score_action = "monitor"
            else:
                score_action = "allow"

            # Session floor
            session_class = behavior.get("classification", "clean")
            if session_class == "hostile":
                session_floor = "challenge"
            elif session_class == "suspicious":
                session_floor = "monitor"
            else:
                session_floor = "allow"

            # Apply override
            if override_action:
                decision = override_action
                decision_logic = f"override={override_action}"
            else:
                action_rank = {"allow": 0, "monitor": 1, "challenge": 2, "block": 3}
                candidate_actions = [score_action, session_floor]
                final_decision = max(candidate_actions, key=lambda a: action_rank.get(a, 0))
                decision = final_decision
                decision_logic = f"score_action={score_action}, session_floor={session_floor} -> {final_decision}"

            # Category-based minimum actions (Arjuna & Shakuni)
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

            # ---- NEW: Override based on secret severity and policy action ----
            secret_severity = hanuman.get("secret_severity")
            detected_secrets = hanuman.get("detected_secrets", [])
            policy_action = yudhishthira.get("policy_action")
            if secret_severity == "critical":
                decision = "block"
                decision_logic = "secret_severity=critical -> block"
            elif policy_action == "block":
                decision = "block"
                decision_logic = f"policy_action={policy_action} -> block"
            elif detected_secrets:
                if action_rank.get(decision, 0) < action_rank.get("challenge", 0):
                    decision = "challenge"
                    decision_logic += " (secrets detected -> challenge)"

            # Compute overall confidence (simplified)
            confidence = 0.95 if decision in ["block", "challenge"] else 0.7

            # Status
            degraded_engines = [name for name, r in engine_results.items() if isinstance(r, dict) and r.get("status") == "degraded"]
            fallback_used = len(degraded_engines) > 0
            status = "degraded" if fallback_used else "ok"

            # Build trace
            trace = {
                "trace_version": self.trace_version,
                "status": status,
                "confidence": confidence,
                "deception_labels": shakuni_labels,
                "arjuna_label": arjuna_label,
                "arjuna_confidence": arjuna_conf,
                "arjuna_reason": arjuna.get("reason", ""),
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
                "session_classification": session_class,
                "session_reason": behavior_reason,
                "threat_session_modifier": round(threat_session_modifier, 2),
                "threat_global_modifier": round(threat_global_modifier, 2),
                "kautilya_path": kautilya_info.get("path"),
                "kautilya_reason": kautilya_info.get("reason"),
                "sensitivity_label": classification.get("sensitivity_label", "LOW"),
                "data_categories": classification.get("data_categories", []),
                "secret_severity": secret_severity,
                "hanuman_detected_secrets": detected_secrets,
                "policy_action": policy_action,
                "policy_reason_codes": yudhishthira.get("reason_codes", []),
            }
            if override_action:
                trace["override"] = override_action
                trace["override_reason"] = override_reason

            external_score = int(round(modified_score * 100))
            return {
                "engine": "krishna",
                "score": external_score,
                "normalized_score": round(modified_score, 3),
                "decision": decision,
                "details": {"trace": trace},
            }
        except Exception as e:
            # Fail‑closed fallback
            return {
                "engine": "krishna",
                "status": "error",
                "decision": "challenge",
                "score": 95,
                "normalized_score": 0.95,
                "decision_logic": f"krishna_error_fallback: {str(e)}",
                "details": {"trace": {"error": str(e)}}
            }
'''
path.write_text(full_krishna)
print("✅ Restored full Krishna with weighted scoring + secret/policy overrides.")
