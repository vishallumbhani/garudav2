"""
Rule engine (regex/keyword) with YAML configuration.
"""

import re
import yaml
from pathlib import Path
from typing import Dict, Any, List

class Bhishma:
    def __init__(self):
            rules_path = Path(__file__).parent / "rules.yaml"

            if not rules_path.exists():
                raise RuntimeError("Bhishma rules file missing")

            try:
                with open(rules_path) as f:
                    data = yaml.safe_load(f)
            except Exception as e:
                raise RuntimeError(f"Failed to load Bhishma rules: {e}")

            self.rules = {
                "critical": data.get("critical_patterns", []),
                "sensitive": data.get("sensitive_patterns", []),
                "warning": data.get("warning_patterns", [])
            }

    def run(self, request, hanuman_result) -> Dict[str, Any]:
        if request.normalized_text is not None:
            text = request.normalized_text
        else:
            text = request.content
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='ignore')

        matched = []
        highest_score = 0.0
        reason = ""

        # Check critical patterns first (highest impact)
        for pattern_info in self.rules.get("critical", []):
            if re.search(pattern_info["pattern"], text, re.IGNORECASE):
                matched.append(pattern_info)
                highest_score = max(highest_score, pattern_info["severity"])
                reason = f"Critical pattern: {pattern_info['pattern']}"

        # If no critical, check sensitive
        if not matched:
            for pattern_info in self.rules.get("sensitive", []):
                if re.search(pattern_info["pattern"], text, re.IGNORECASE):
                    matched.append(pattern_info)
                    highest_score = max(highest_score, pattern_info["severity"])
                    reason = f"Sensitive pattern: {pattern_info['pattern']}"

        # If still no match, check warning
        if not matched:
            for pattern_info in self.rules.get("warning", []):
                if re.search(pattern_info["pattern"], text, re.IGNORECASE):
                    matched.append(pattern_info)
                    highest_score = max(highest_score, pattern_info["severity"])
                    reason = f"Warning pattern: {pattern_info['pattern']}"

        if not matched:
            highest_score = 0.1
            reason = "No patterns matched."

        return {
            "engine": "bhishma",
            "status": "ok",
            "score": round(highest_score, 2),
            "confidence": 0.8 if highest_score > 0.5 else 0.6,
            "labels": [p.get("type", "unknown") for p in matched],
            "reason": reason,
            "matched_patterns": matched
        }
