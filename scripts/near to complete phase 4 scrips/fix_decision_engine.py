#!/usr/bin/env python3
"""
Fix the decision engine:
- Add category-based minimum actions based on Arjuna label and Shakuni labels.
- Expand Bhishma rules with broader patterns.
- Add more Shakuni intent families.
"""

import os
import yaml
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

# ----------------------------------------------------------------------
# 1. Update Krishna with category-based floors
# ----------------------------------------------------------------------
krishna_path = PROJECT_ROOT / "src" / "engines" / "krishna" / "engine.py"
with open(krishna_path, "r") as f:
    krishna = f.read()

# We'll insert a new function inside the `run` method, after we have the
# score_action and session_floor, but before final decision.
# We'll replace the decision block with one that also considers category floors.

# Find the part where decision is computed (after override check).
# The current code has:
#   if override_action:
#       decision = override_action
#       decision_logic = f"override={override_action}"
#   else:
#       # ... score-based decision
#   # Then session floor enforcement
#
# We'll insert category-based floors after the session floor.

# We'll add a new section that:
# - If Arjuna label is data_exfiltration and confidence >= 0.8, set floor to challenge.
# - If Arjuna label is policy_bypass and confidence >= 0.75, set floor to challenge.
# - If any Shakuni label in a list, set floor to challenge.

# We'll insert it right after the session floor enforcement.

# First, locate the block where session floor is applied.
# It currently looks like:
#   if decision_order.get(decision, 0) < decision_order.get(min_decision, 0):
#       decision = min_decision
#       decision_logic += f" (session floor: {min_decision})"
# We'll add our new floors before that, and adjust the final decision accordingly.

new_code = '''
        # ------------------------------------------------------------------
        # Category-based minimum actions (Arjuna & Shakuni)
        # ------------------------------------------------------------------
        arjuna_label = arjuna.get("label", "")
        arjuna_conf = arjuna.get("confidence", 0.0)
        shakuni_labels = shakuni.get("labels", [])

        category_floor = "allow"
        if arjuna_label == "data_exfiltration" and arjuna_conf >= 0.80:
            category_floor = "challenge"
        elif arjuna_label == "policy_bypass" and arjuna_conf >= 0.75:
            category_floor = "challenge"

        # Check Shakuni labels
        high_intent_labels = [
            "covert_exfiltration_intent",
            "authentication_bypass_intent",
            "secret_extraction_intent",
            "data_theft_intent",
            "evasion_intent",
            "restriction_avoidance_intent",
            "control_disable_intent",
        ]
        for label in shakuni_labels:
            if label in high_intent_labels:
                category_floor = "challenge"
                break

        # Apply the stricter floor
        if decision_order.get(decision, 0) < decision_order.get(category_floor, 0):
            decision = category_floor
            decision_logic += f" (category floor: {category_floor})"
'''

# Insert after the session floor block (we need to find that block)
# The session floor block is already there; we'll add our code right after it.
# We'll replace the line where session floor is applied with a larger block that includes our new logic.
# But to be safe, we'll insert after the session floor block ends.

# Find the line that says "decision_order.get(decision, 0) < decision_order.get(min_decision, 0)"
# That line is inside the session floor enforcement. We'll insert our new code after the closing brace of that if.
# Actually easier: we'll add our new code before the session floor block, so we can apply floors in order: first session floor, then category floor, then override.
# But the order should be: override > category floor > session floor? Actually override is strongest, then category floor, then session floor.
# We'll apply after override but before session floor.

# Find the line after the override block:
#   else:
#       # ... score-based decision
#   decision_logic = f"score={modified_score:.3f} -> {decision}"
#   # Session floor block follows.
# We'll insert after that decision_logic line.

# Let's look for the pattern "decision_logic = f\"score={modified_score:.3f} -> {decision}\""
if 'decision_logic = f"score={modified_score:.3f} -> {decision}"' in krishna:
    insert_point = 'decision_logic = f"score={modified_score:.3f} -> {decision}"'
    krishna = krishna.replace(insert_point, insert_point + new_code)
else:
    # Fallback: maybe it's different. We'll add after the else block.
    # We'll search for a line that sets decision_logic after the else.
    # We'll just add it after the session floor block? But session floor is after.
    # We'll add it before the session floor block.
    # Find the line that starts with "# Session-based decision floor"
    if "# Session-based decision floor" in krishna:
        krishna = krishna.replace("# Session-based decision floor", new_code + "\n\n        # Session-based decision floor")
    else:
        print("Warning: Could not find insertion point for category floors.")

with open(krishna_path, "w") as f:
    f.write(krishna)
print("Updated Krishna with category-based minimum actions.")

# ----------------------------------------------------------------------
# 2. Expand Bhishma rules with broader patterns
# ----------------------------------------------------------------------
bhishma_rules_path = PROJECT_ROOT / "src" / "engines" / "bhishma" / "rules.yaml"
with open(bhishma_rules_path, "r") as f:
    rules = yaml.safe_load(f)

# Add new patterns for policy bypass and data exfiltration
new_critical = [
    {"pattern": r"(?i)(bypass|evade|circumvent|avoid|dodge).*?(auth|security|filter|restriction|control)", "severity": 0.85, "type": "critical"},
    {"pattern": r"(?i)(exfiltrate|leak|steal|export|copy).*?(data|files|keys|records|secrets|database)", "severity": 0.90, "type": "critical"},
    {"pattern": r"(?i)(without detection|covert|quietly|secretly|hidden|stealth)", "severity": 0.80, "type": "critical"},
]

# Add to critical_patterns (or create a new category if needed)
if "critical_patterns" in rules:
    rules["critical_patterns"].extend(new_critical)
else:
    rules["critical_patterns"] = new_critical

with open(bhishma_rules_path, "w") as f:
    yaml.dump(rules, f, default_flow_style=False, allow_unicode=True)
print("Expanded Bhishma rules with broader patterns.")

# ----------------------------------------------------------------------
# 3. Expand Shakuni with more intent families
# ----------------------------------------------------------------------
shakuni_path = PROJECT_ROOT / "src" / "engines" / "shakuni" / "engine.py"
with open(shakuni_path, "r") as f:
    shakuni_content = f.read()

# Add new pattern lists
new_families = """
        self.evasion_intent_patterns = [
            r"(?i)evade (detection|monitoring|audit)",
            r"(?i)avoid detection",
            r"(?i)stay undetected",
            r"(?i)fly under the radar",
            r"(?i)avoid raising alarms",
        ]
        self.restriction_avoidance_patterns = [
            r"(?i)avoid restrictions",
            r"(?i)dodge (rules|filters|controls)",
            r"(?i)get around (block|limit)",
            r"(?i)circumvent (policy|safeguards)",
        ]
        self.control_disable_patterns = [
            r"(?i)disable (security|safety|content) controls",
            r"(?i)turn off (filters|monitoring)",
            r"(?i)deactivate (protection|restrictions)",
        ]
        self.secret_extraction_patterns = [
            r"(?i)extract (secret|key|token|password)",
            r"(?i)reveal (hidden|confidential|internal)",
            r"(?i)dump (system|database) (info|data)",
            r"(?i)get (api key|credentials)",
        ]
        self.data_theft_patterns = [
            r"(?i)steal (data|records|files)",
            r"(?i)copy sensitive (information|documents)",
            r"(?i)export customer (data|information)",
            r"(?i)download (confidential|proprietary)",
        ]
        self.covert_transfer_patterns = [
            r"(?i)covert (transfer|movement)",
            r"(?i)hide (stolen|exfiltrated) data",
            r"(?i)secretly (move|send)",
            r"(?i)without being noticed",
        ]
"""
# Insert after existing pattern definitions (e.g., after dan_patterns)
if "self.dan_patterns = [" in shakuni_content:
    shakuni_content = shakuni_content.replace("self.dan_patterns = [", new_families + "\n        self.dan_patterns = [")
else:
    print("Warning: Could not find dan_patterns in shakuni.py. Skipping.")

# Add check_category calls for the new families
run_insert = """
        check_category(self.evasion_intent_patterns, "evasion_intent", 0.30)
        check_category(self.restriction_avoidance_patterns, "restriction_avoidance_intent", 0.25)
        check_category(self.control_disable_patterns, "control_disable_intent", 0.35)
        check_category(self.secret_extraction_patterns, "secret_extraction_intent", 0.40)
        check_category(self.data_theft_patterns, "data_theft_intent", 0.40)
        check_category(self.covert_transfer_patterns, "covert_transfer_intent", 0.35)
"""
if "check_category(self.dan_patterns" in shakuni_content:
    shakuni_content = shakuni_content.replace(
        "check_category(self.dan_patterns",
        run_insert + "\n        check_category(self.dan_patterns"
    )
else:
    print("Warning: Could not find dan_patterns check in run method.")

with open(shakuni_path, "w") as f:
    f.write(shakuni_content)
print("Expanded Shakuni with new intent families.")

print("\n✅ Decision engine, Bhishma, and Shakuni enhanced.")
print("Restart server and test again.")
