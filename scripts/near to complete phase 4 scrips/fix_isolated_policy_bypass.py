#!/usr/bin/env python3
"""
Add stricter decision floors for policy_bypass in isolated mode.
"""

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

krishna_path = PROJECT_ROOT / "src" / "engines" / "krishna" / "engine.py"
with open(krishna_path, "r") as f:
    krishna = f.read()

# We'll insert a new section after the existing category floor logic.
# We'll find where the category floor is computed and add our new rules there.

# Look for the line where category_floor is defined. It should be near:
#   category_floor = "allow"
#   if arjuna_label == "data_exfiltration" and arjuna_conf >= 0.80:
#       category_floor = "challenge"
#   elif arjuna_label == "policy_bypass" and arjuna_conf >= 0.85:
#       category_floor = "challenge"
#   ...

# We'll replace that block with a more comprehensive one that also checks Shakuni labels.
# But to be safe, we'll insert after the existing block (if it exists) or create one.

# First, find the line where the category floor is set. It may have been added earlier.
# We'll search for "category_floor = "allow"". If not found, we'll add the whole block.

if "category_floor = \"allow\"" in krishna:
    # Replace the existing category floor block with a new one that includes the new rules.
    # We'll locate the block from that line until the next line that starts with "# Session-based decision floor" or similar.
    pattern = r'(# Category-based minimum actions.*?)(?=# Session-based decision floor)'
    new_floor = '''
        # ------------------------------------------------------------------
        # Category-based minimum actions (Arjuna & Shakuni) - tightened
        # ------------------------------------------------------------------
        arjuna_label = arjuna.get("label", "")
        arjuna_conf = arjuna.get("confidence", 0.0)
        shakuni_labels = shakuni.get("labels", [])

        category_floor = "allow"
        # Data exfiltration with high confidence -> challenge
        if arjuna_label == "data_exfiltration" and arjuna_conf >= 0.80:
            category_floor = "challenge"
        # Policy bypass with high confidence -> challenge (isolated mode)
        if arjuna_label == "policy_bypass" and arjuna_conf >= 0.85:
            category_floor = "challenge"
        # Additional Shakuni intents -> challenge
        if "indirect_bypass_phrasing" in shakuni_labels or "hypothetical_justification" in shakuni_labels:
            category_floor = "challenge"
        # High‑intent labels from Shakuni (keep existing)
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

        # Apply the stricter floor (if it is stronger than current decision)
        if decision_order.get(decision, 0) < decision_order.get(category_floor, 0):
            decision = category_floor
            decision_logic += f" (category floor: {category_floor})"
'''
    krishna = re.sub(pattern, new_floor, krishna, flags=re.DOTALL)
else:
    # If the category floor block doesn't exist, we need to insert it before the session floor.
    # Find the session floor block and insert our block right before it.
    session_floor_marker = "# Session-based decision floor"
    if session_floor_marker in krishna:
        insert_code = '''
        # ------------------------------------------------------------------
        # Category-based minimum actions (Arjuna & Shakuni) - tightened
        # ------------------------------------------------------------------
        arjuna_label = arjuna.get("label", "")
        arjuna_conf = arjuna.get("confidence", 0.0)
        shakuni_labels = shakuni.get("labels", [])

        category_floor = "allow"
        # Data exfiltration with high confidence -> challenge
        if arjuna_label == "data_exfiltration" and arjuna_conf >= 0.80:
            category_floor = "challenge"
        # Policy bypass with high confidence -> challenge (isolated mode)
        if arjuna_label == "policy_bypass" and arjuna_conf >= 0.85:
            category_floor = "challenge"
        # Additional Shakuni intents -> challenge
        if "indirect_bypass_phrasing" in shakuni_labels or "hypothetical_justification" in shakuni_labels:
            category_floor = "challenge"
        # High‑intent labels from Shakuni
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

        # Apply the stricter floor (if it is stronger than current decision)
        if decision_order.get(decision, 0) < decision_order.get(category_floor, 0):
            decision = category_floor
            decision_logic += f" (category floor: {category_floor})"
'''
        krishna = krishna.replace(session_floor_marker, insert_code + "\n\n" + session_floor_marker)
    else:
        print("Could not find insertion point. Manual edit may be needed.")
        exit(1)

with open(krishna_path, "w") as f:
    f.write(krishna)

print("✅ Added stricter policy_bypass decision floors.")
print("Restart server and test isolated mode again.")
