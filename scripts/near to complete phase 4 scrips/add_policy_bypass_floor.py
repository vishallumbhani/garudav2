#!/usr/bin/env python3
import re
from pathlib import Path

krishna_path = Path("src/engines/krishna/engine.py")
with open(krishna_path, "r") as f:
    content = f.read()

# Find the line that sets decision_logic (the one with "score_action=")
# We'll search for a pattern that includes "score_action=" and "session_floor="
pattern = r'(decision_logic = f"score_action={score_action}, session_floor={session_floor} -> {decision}")'

if not re.search(pattern, content):
    print("Could not find the decision_logic line. Manual edit needed.")
    print("Please add the following block after the line that sets decision_logic.")
    print("See script output for the block.")
    exit(1)

# We'll insert after that line
new_block = '''
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

        # Ensure decision_order exists (it should)
        if 'decision_order' not in locals():
            decision_order = {"allow": 0, "monitor": 1, "challenge": 2, "block": 3}
        if decision_order.get(decision, 0) < decision_order.get(category_floor, 0):
            decision = category_floor
            decision_logic += f" (category floor: {category_floor})"
'''

# Insert after the pattern
content = re.sub(pattern, r'\1' + new_block, content)

with open(krishna_path, "w") as f:
    f.write(content)
print("Added policy_bypass floor after decision_logic.")
