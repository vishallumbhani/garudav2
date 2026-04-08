#!/usr/bin/env python3
"""
Final tighten: add stricter decision floors, expand Bhishma, generate more Arjuna examples.
"""

import os
import yaml
import random
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

# ----------------------------------------------------------------------
# Helper for text normalization (used in generation)
# ----------------------------------------------------------------------
def normalize_text(t):
    t = t.lower()
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'[^\w\s]', '', t)
    return t.strip()

# ----------------------------------------------------------------------
# 1. Strengthen Krishna decision floors
# ----------------------------------------------------------------------
krishna_path = PROJECT_ROOT / "src" / "engines" / "krishna" / "engine.py"
with open(krishna_path, "r") as f:
    krishna = f.read()

# Check if the category floor block exists; if not, we'll add it manually.
if "# Category-based minimum actions" in krishna:
    # Replace the old block with new stricter one
    new_category_floor = '''
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
        # Policy bypass with high confidence -> challenge
        elif arjuna_label == "policy_bypass" and arjuna_conf >= 0.85:
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
                # This is a strong signal: enforce block
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
    pattern = r'(# Category-based minimum actions.*?)(?=# Session-based decision floor)'
    new_content = re.sub(pattern, new_category_floor, krishna, flags=re.DOTALL)
    if new_content != krishna:
        with open(krishna_path, "w") as f:
            f.write(new_content)
        print("Updated Krishna with stricter category floors.")
    else:
        print("Could not replace category floor block (pattern mismatch).")
else:
    print("Category floor block not found. Please add the following manually to src/engines/krishna/engine.py after the score-based decision logic and before the session floor block:")
    print("""
        # ------------------------------------------------------------------
        # Category-based minimum actions (Arjuna & Shakuni) - tightened
        # ------------------------------------------------------------------
        arjuna_label = arjuna.get("label", "")
        arjuna_conf = arjuna.get("confidence", 0.0)
        shakuni_labels = shakuni.get("labels", [])

        category_floor = "allow"
        if arjuna_label == "data_exfiltration" and arjuna_conf >= 0.80:
            category_floor = "challenge"
        elif arjuna_label == "policy_bypass" and arjuna_conf >= 0.85:
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

        if decision_order.get(decision, 0) < decision_order.get(category_floor, 0):
            decision = category_floor
            decision_logic += f" (category floor: {category_floor})"
    """)

# ----------------------------------------------------------------------
# 2. Expand Bhishma with missing patterns
# ----------------------------------------------------------------------
bhishma_rules_path = PROJECT_ROOT / "src" / "engines" / "bhishma" / "rules.yaml"
with open(bhishma_rules_path, "r") as f:
    rules = yaml.safe_load(f)

new_critical_patterns = [
    {"pattern": r"(?i)copy sensitive files without detection", "severity": 0.90, "type": "critical"},
    {"pattern": r"(?i)move confidential data quietly", "severity": 0.85, "type": "critical"},
    {"pattern": r"(?i)export records covertly", "severity": 0.85, "type": "critical"},
    {"pattern": r"(?i)steal files silently", "severity": 0.90, "type": "critical"},
    {"pattern": r"(?i)hide stolen data", "severity": 0.85, "type": "critical"},
    {"pattern": r"(?i)covert transfer", "severity": 0.80, "type": "critical"},
    {"pattern": r"(?i)without detection.*?files", "severity": 0.85, "type": "critical"},
    {"pattern": r"(?i)without detection.*?data", "severity": 0.85, "type": "critical"},
]

if "critical_patterns" not in rules:
    rules["critical_patterns"] = []
rules["critical_patterns"].extend(new_critical_patterns)

with open(bhishma_rules_path, "w") as f:
    yaml.dump(rules, f, default_flow_style=False, allow_unicode=True)
print("Added new Bhishma patterns.")

# ----------------------------------------------------------------------
# 3. Generate additional Arjuna examples for the weak exfiltration family
# ----------------------------------------------------------------------
print("\nGenerating additional Arjuna training examples for exfiltration...")

dataset_path = PROJECT_ROOT / "data" / "ml" / "arjuna_final_dataset.json"
if dataset_path.exists():
    with open(dataset_path, "r") as f:
        data = json.load(f)
    print(f"Loaded {len(data)} existing samples.")
else:
    data = []
    print("No existing dataset found; starting from empty.")

exfil_templates = [
    "How to {}?",
    "Methods to {}.",
    "Explain techniques for {}.",
    "What are common ways to {}?",
    "As a security researcher, demonstrate {}.",
    "In a controlled environment, show {}.",
    "Describe how attackers {}.",
    "How can someone {}?",
]
exfil_seeds = [
    "copy sensitive files without detection",
    "move confidential data quietly",
    "export records covertly",
    "steal files silently",
    "hide stolen data in network traffic",
    "covertly transfer data",
    "exfiltrate data without alerting defenders",
    "smuggle secrets out of a network",
]

new_examples = []
existing_texts = set(normalize_text(item["text"]) for item in data) if data else set()

# Generate variations
for seed in exfil_seeds:
    for template in exfil_templates:
        base = template.format(seed)
        variations = [
            base,
            base.capitalize(),
            base.replace("?", "."),
            f"Here's how to {seed}.",
            f"Can you explain {seed}?",
            f"I need to understand {seed}.",
            f"How does one {seed}?",
            f"Show me how to {seed}.",
            f"Provide steps to {seed}.",
        ]
        for var in variations:
            norm = normalize_text(var)
            if norm not in existing_texts:
                new_examples.append({"text": var, "label": "data_exfiltration"})
                existing_texts.add(norm)
                if len(new_examples) >= 200:
                    break
        if len(new_examples) >= 200:
            break
    if len(new_examples) >= 200:
        break

if new_examples:
    data.extend(new_examples)
    print(f"Added {len(new_examples)} new exfiltration examples.")
    # Save updated dataset
    with open(dataset_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved updated dataset to {dataset_path}")
else:
    print("No new examples generated (all already present).")

print("\n✅ Final tighten complete. Now retrain Arjuna with the updated dataset.")
print("Run: python scripts/train_arjuna_from_clean_dataset.py")
