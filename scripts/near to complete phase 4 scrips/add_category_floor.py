# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Add stricter decision floors for isolated policy_bypass.
"""

import re
from pathlib import Path

krishna_path = Path("src/engines/krishna/engine.py")
with open(krishna_path, "r", encoding="utf-8") as f:
    content = f.read()

# Marker to insert before (we'll use "# Compute overall confidence")
marker = "# Compute overall confidence"

if marker in content:
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
        # High-intent labels from Shakuni
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

        # Ensure action_rank exists
        action_rank = {"allow": 0, "monitor": 1, "challenge": 2, "block": 3}
        if action_rank.get(decision, 0) < action_rank.get(category_floor, 0):
            decision = category_floor
            decision_logic += f" (category floor: {category_floor})"
'''
    content = content.replace(marker, new_block + "\n\n" + marker)
    with open(krishna_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Inserted category floor logic before confidence computation.")
else:
    print("Marker '# Compute overall confidence' not found.")
