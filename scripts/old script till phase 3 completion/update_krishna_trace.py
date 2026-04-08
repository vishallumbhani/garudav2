from pathlib import Path

path = Path("src/engines/krishna/engine.py")
content = path.read_text()

# Find the trace building section and replace it with a version that merges all engine results.
# We'll look for the line where trace = { and replace the whole block.

# First, we'll completely replace the run method with a robust version that builds trace from engine_results.
new_content = '''"""
Decision aggregator – safe version with fail‑closed and integer score.
"""

from typing import Dict, Any

class Krishna:
    def __init__(self):
        self.weights = {"bhishma": 0.5, "hanuman": 0.2, "shakuni": 0.15, "arjuna": 0.15}
        self.trace_version = "1.1"

    def run(self, request, engine_results: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Extract Hanuman and Yudhishthira info
            hanuman_info = engine_results.get("hanuman", {})
            yudhishthira_info = engine_results.get("yudhishthira", {})
            shakuni_info = engine_results.get("shakuni", {})
            arjuna_info = engine_results.get("arjuna", {})
            classification_info = engine_results.get("data_classification", {})
            kautilya_info = engine_results.get("kautilya", {})
            behavior_info = engine_results.get("behavior", {})
            threat_memory_info = engine_results.get("threat_memory", {})

            # Collect all trace fields from engines
            trace = {
                # Hanuman fields
                "hanuman_content_kind": hanuman_info.get("content_kind"),
                "hanuman_risk_hint": hanuman_info.get("risk_hint"),
                "hanuman_complexity": hanuman_info.get("complexity"),
                "hanuman_likely_family": hanuman_info.get("likely_family"),
                "hanuman_line_count": hanuman_info.get("line_count"),
                "hanuman_section_count": hanuman_info.get("section_count"),
                "hanuman_has_code_blocks": hanuman_info.get("has_code_blocks"),
                "hanuman_has_stack_trace": hanuman_info.get("has_stack_trace"),
                "hanuman_has_secrets_pattern": hanuman_info.get("has_secrets_pattern"),
                "hanuman_detected_secrets": hanuman_info.get("detected_secrets", []),
                "secret_severity": hanuman_info.get("secret_severity"),
                "hanuman_detected_dangerous_functions": hanuman_info.get("detected_dangerous_functions", []),
                "hanuman_code_risk_hint": hanuman_info.get("code_risk_hint"),
                "hanuman_code_risk_reason": hanuman_info.get("code_risk_reason"),
                "hanuman_summary_chunk_count": hanuman_info.get("summary", {}).get("chunk_count", 0),
                "hanuman_summary_suspicious_phrases": hanuman_info.get("summary", {}).get("suspicious_phrases", []),
                "hanuman_summary_top_keywords": hanuman_info.get("summary", {}).get("top_keywords", []),
                # Shakuni fields
                "deception_labels": shakuni_info.get("labels", []),
                # Arjuna fields
                "arjuna_label": arjuna_info.get("label"),
                "arjuna_confidence": arjuna_info.get("confidence"),
                "arjuna_reason": arjuna_info.get("reason"),
                # Classification fields
                "sensitivity_label": classification_info.get("sensitivity_label", "LOW"),
                "data_categories": classification_info.get("data_categories", []),
                "pii_detected": classification_info.get("pii_detected", False),
                "pii_types": classification_info.get("pii_types", []),
                "finance_detected": classification_info.get("finance_detected", False),
                "finance_types": classification_info.get("finance_types", []),
                "credential_detected": classification_info.get("credential_detected", False),
                "trade_secret_detected": classification_info.get("trade_secret_detected", False),
                "phi_detected": classification_info.get("phi_detected", False),
                "classification_reason": classification_info.get("classification_reason", ""),
                # Yudhishthira policy fields
                "policy_action": yudhishthira_info.get("policy_action"),
                "policy_reason_codes": yudhishthira_info.get("reason_codes", []),
                # Kautilya routing
                "kautilya_path": kautilya_info.get("path"),
                "kautilya_reason": kautilya_info.get("reason"),
                "kautilya_engines_run": kautilya_info.get("engines_run", []),
                "kautilya_engines_skipped": kautilya_info.get("engines_skipped", []),
                "kautilya_cost_tier": kautilya_info.get("cost_tier"),
                "kautilya_latency_budget_ms": kautilya_info.get("latency_budget_ms"),
                # Behavior
                "session_classification": behavior_info.get("classification"),
                "session_reason": behavior_info.get("escalation_reason"),
                "session_high_risk_count": behavior_info.get("high_risk_count", 0),
                "session_max_risk": behavior_info.get("max_risk", 0),
                # Threat memory
                "threat_session_modifier": threat_memory_info.get("session_modifier", 1.0),
                "threat_global_modifier": threat_memory_info.get("global_modifier", 1.0),
                # Base scores and weights (from earlier computation)
                "weights": self.weights,
                "scores": {
                    "bhishma": engine_results.get("bhishma", {}).get("score", 0.5),
                    "hanuman": hanuman_info.get("score", 0.5),
                    "shakuni": shakuni_info.get("score", 0.5),
                    "arjuna": arjuna_info.get("score", 0.5),
                },
            }

            # Determine decision based on severity and policy
            detected_secrets = hanuman_info.get("detected_secrets", [])
            secret_severity = hanuman_info.get("secret_severity")
            policy_action = yudhishthira_info.get("policy_action")

            decision = "allow"
            score = 0
            decision_logic = "No policy or secret override"

            if secret_severity == "critical":
                decision = "block"
                score = 95
                decision_logic = "secret_severity=critical -> block"
            elif policy_action == "block":
                decision = "block"
                score = 90
                decision_logic = f"policy_action={policy_action} -> block"
            elif detected_secrets:
                decision = "challenge"
                score = 75
                decision_logic = f"detected_secrets={detected_secrets} -> challenge"

            score = int(round(score))
            trace["decision_logic"] = decision_logic

            return {
                "engine": "krishna",
                "status": "ok",
                "decision": decision,
                "score": score,
                "normalized_score": score / 100.0,
                "details": {"trace": trace},
                "decision_logic": decision_logic,
            }
        except Exception as e:
            # Fail‑closed fallback with minimal trace
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
path.write_text(new_content)
print("✅ Updated Krishna to include full trace from all engines.")
