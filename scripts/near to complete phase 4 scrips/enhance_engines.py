#!/usr/bin/env python3
"""
Enhance Bhishma, Shakuni, and Krishna based on test feedback.
"""

import os
import yaml
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

# ----------------------------------------------------------------------
# 1. Expand Bhishma rules
# ----------------------------------------------------------------------
bhishma_rules_path = PROJECT_ROOT / "src" / "engines" / "bhishma" / "rules.yaml"
with open(bhishma_rules_path, "r") as f:
    rules = yaml.safe_load(f)

# Add new patterns to existing categories
# We'll append to the existing lists.

new_critical = [
    {"pattern": "(?i)pretend (you are|to be|you're)", "severity": 0.80, "type": "critical"},
    {"pattern": "(?i)act as (if|though|a)", "severity": 0.80, "type": "critical"},
    {"pattern": "(?i)roleplay as", "severity": 0.80, "type": "critical"},
    {"pattern": "(?i)developer console", "severity": 0.85, "type": "critical"},
    {"pattern": "(?i)debugging mode", "severity": 0.85, "type": "critical"},
    {"pattern": "(?i)reveal internal instructions", "severity": 0.90, "type": "critical"},
    {"pattern": "(?i)bypass authentication", "severity": 0.80, "type": "critical"},
    {"pattern": "(?i)evade moderation", "severity": 0.75, "type": "critical"},
    {"pattern": "(?i)circumvent controls", "severity": 0.80, "type": "critical"},
]

new_sensitive = [
    {"pattern": "(?i)extract API keys", "severity": 0.70, "type": "sensitive"},
    {"pattern": "(?i)export customer data", "severity": 0.70, "type": "sensitive"},
    {"pattern": "(?i)steal (database|secrets|credentials)", "severity": 0.75, "type": "sensitive"},
]

# Append to existing lists
rules["critical_patterns"].extend(new_critical)
rules["sensitive_patterns"].extend(new_sensitive)

with open(bhishma_rules_path, "w") as f:
    yaml.dump(rules, f, default_flow_style=False, allow_unicode=True)
print("Updated Bhishma rules with new patterns.")

# ----------------------------------------------------------------------
# 2. Expand Shakuni label families
# ----------------------------------------------------------------------
shakuni_path = PROJECT_ROOT / "src" / "engines" / "shakuni" / "engine.py"
with open(shakuni_path, "r") as f:
    shakuni_content = f.read()

# We'll extend the existing patterns by adding new lists in the __init__ method.
# We'll search for the self.indirect_bypass_patterns definition and add new families after it.
new_families = """
        self.red_team_patterns = [
            r"(?i)red team",
            r"(?i)redteam",
            r"(?i)penetration test",
            r"(?i)authorized security test",
            r"(?i)as a red team member",
        ]
        self.research_justification_patterns = [
            r"(?i)for research purposes",
            r"(?i)academic study",
            r"(?i)doctoral research",
            r"(?i)university project",
            r"(?i)scientific investigation",
        ]
        self.secret_extraction_patterns = [
            r"(?i)extract API key",
            r"(?i)leak (token|password|secret)",
            r"(?i)reveal confidential",
            r"(?i)dump database",
            r"(?i)export customer data",
            r"(?i)steal credentials",
        ]
        self.covert_exfiltration_patterns = [
            r"(?i)exfiltrate (data|records)",
            r"(?i)covert transfer",
            r"(?i)hide stolen",
            r"(?i)dns tunneling",
            r"(?i)stealthy data movement",
        ]
        self.authentication_bypass_patterns = [
            r"(?i)bypass (authentication|login|2FA|MFA)",
            r"(?i)circumvent authentication",
            r"(?i)avoid (login|security check)",
            r"(?i)disable (security|auth) controls",
        ]
        self.policy_evasion_patterns = [
            r"(?i)evade (moderation|content policy|safety filters)",
            r"(?i)bypass (policy|rules|content filters)",
            r"(?i)avoid detection by",
            r"(?i)dodge restrictions",
        ]
"""
# Insert after the existing indirect_bypass_patterns block
# We'll find the line where self.dan_patterns ends and insert new families before it.
# This is a bit fragile, but we'll do a simple replace after a known marker.
if "self.dan_patterns = [" in shakuni_content:
    # Insert new families before the dan_patterns definition
    shakuni_content = shakuni_content.replace("self.dan_patterns = [", new_families + "\n        self.dan_patterns = [")
else:
    print("Warning: Could not find dan_patterns in shakuni.py. Skipping.")

# Also update the run method to call check_category for each new family
# We'll add the checks after the existing ones.
# Find the line where check_category for dan_patterns is called, and add before or after.
run_method_insert = """
        check_category(self.red_team_patterns, "red_team_justification", 0.25)
        check_category(self.research_justification_patterns, "research_justification", 0.20)
        check_category(self.secret_extraction_patterns, "secret_extraction_intent", 0.35)
        check_category(self.covert_exfiltration_patterns, "covert_exfiltration_intent", 0.30)
        check_category(self.authentication_bypass_patterns, "authentication_bypass_intent", 0.30)
        check_category(self.policy_evasion_patterns, "policy_evasion_intent", 0.25)
"""
# Insert after the line that calls check_category for dan_patterns
if "check_category(self.dan_patterns" in shakuni_content:
    shakuni_content = shakuni_content.replace(
        "check_category(self.dan_patterns",
        run_method_insert + "\n        check_category(self.dan_patterns"
    )
else:
    print("Warning: Could not find dan_patterns check in run method.")

with open(shakuni_path, "w") as f:
    f.write(shakuni_content)
print("Expanded Shakuni with new deception families.")

# ----------------------------------------------------------------------
# 3. Improve Krishna decision logic output
# ----------------------------------------------------------------------
krishna_path = PROJECT_ROOT / "src" / "engines" / "krishna" / "engine.py"
with open(krishna_path, "r") as f:
    krishna_content = f.read()

# We'll modify the trace dictionary to include more explicit fields:
# - raw_score_action (the action based solely on weighted score)
# - session_floor (the minimum action based on session class)
# - policy_override (if Yudhishthira overrides)
# - final_action (the final decision)
# And ensure decision_logic is a structured string.
# Currently, the trace already includes "score_action", "session_floor", and "decision_logic" (which already shows the combination).
# We'll just ensure they are clearly named and add a "policy_override" if present.

# We'll find where trace is built and add a field for policy_override.
if 'trace = {' in krishna_content:
    # Insert policy_override if override_action is present
    insert_policy_override = '''
            "policy_override": override_action if override_action else None,
            "policy_override_reason": override_reason if override_action else None,
'''
    # Insert after the existing session_floor line
    krishna_content = krishna_content.replace('"session_floor": session_floor,',
                                              '"session_floor": session_floor,\n' + insert_policy_override)

with open(krishna_path, "w") as f:
    f.write(krishna_content)
print("Updated Krishna trace with explicit policy override fields.")

print("\n✅ Engine enhancements complete. Restart server to apply.")
