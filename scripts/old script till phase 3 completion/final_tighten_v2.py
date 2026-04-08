#!/usr/bin/env python3
"""
Final tighten v2:
- Add policy_bypass floor in Krishna.
- Expand Bhishma with missing exfiltration patterns.
- Generate more Arjuna examples for the weak exfiltration family.
"""

import os
import yaml
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

# ----------------------------------------------------------------------
# 1. Add policy_bypass floor in Krishna
# ----------------------------------------------------------------------
krishna_path = PROJECT_ROOT / "src" / "engines" / "krishna" / "engine.py"
with open(krishna_path, "r") as f:
    krishna = f.read()

# Locate the category floor block and add policy_bypass with high confidence.
# We'll add a new condition before the existing ones.
# The block currently has:
#   if arjuna_label == "data_exfiltration" and arjuna_conf >= 0.80:
#       category_floor = "challenge"
#   elif arjuna_label == "policy_bypass" and arjuna_conf >= 0.85:
#       category_floor = "challenge"
# We'll make sure the policy_bypass condition is there with the right threshold.
# We'll also add a separate block for high-confidence policy_bypass that overrides lower floors.

# We'll search for the line where arjuna_label == "data_exfiltration" and insert after it.
if "arjuna_label == \"data_exfiltration\" and arjuna_conf >= 0.80:" in krishna:
    # Insert after that line
    new_lines = '''
        # High-confidence policy bypass -> challenge (even if score low)
        if arjuna_label == "policy_bypass" and arjuna_conf >= 0.85:
            category_floor = "challenge"
'''
    krishna = krishna.replace(
        'if arjuna_label == "data_exfiltration" and arjuna_conf >= 0.80:',
        'if arjuna_label == "data_exfiltration" and arjuna_conf >= 0.80:\n' + new_lines
    )
else:
    # If the block isn't there, add it manually (fallback)
    # We'll add before the high_intent_labels block.
    print("Warning: Could not find data_exfiltration floor. Adding policy_bypass floor manually.")
    # Find the section where high_intent_labels is defined and add before it.
    if "# High‑intent labels from Shakuni" in krishna:
        insert_point = "# High‑intent labels from Shakuni"
        new_block = '''
        # High-confidence policy bypass -> challenge
        if arjuna_label == "policy_bypass" and arjuna_conf >= 0.85:
            category_floor = "challenge"
'''
        krishna = krishna.replace(insert_point, new_block + "\n        " + insert_point)

with open(krishna_path, "w") as f:
    f.write(krishna)
print("Added policy_bypass floor in Krishna.")

# ----------------------------------------------------------------------
# 2. Expand Bhishma with missing exfiltration patterns
# ----------------------------------------------------------------------
bhishma_rules_path = PROJECT_ROOT / "src" / "engines" / "bhishma" / "rules.yaml"
with open(bhishma_rules_path, "r") as f:
    rules = yaml.safe_load(f)

new_patterns = [
    {"pattern": r"(?i)copy sensitive files without detection", "severity": 0.90, "type": "critical"},
    {"pattern": r"(?i)copy confidential files quietly", "severity": 0.85, "type": "critical"},
    {"pattern": r"(?i)move sensitive files covertly", "severity": 0.85, "type": "critical"},
    {"pattern": r"(?i)export records without alerting defenders", "severity": 0.85, "type": "critical"},
    {"pattern": r"(?i)copy files silently", "severity": 0.80, "type": "critical"},
    {"pattern": r"(?i)move confidential data without detection", "severity": 0.85, "type": "critical"},
    {"pattern": r"(?i)steal files covertly", "severity": 0.90, "type": "critical"},
]

if "critical_patterns" not in rules:
    rules["critical_patterns"] = []
rules["critical_patterns"].extend(new_patterns)

with open(bhishma_rules_path, "w") as f:
    yaml.dump(rules, f, default_flow_style=False, allow_unicode=True)
print("Added new Bhishma patterns.")

# ----------------------------------------------------------------------
# 3. Generate more Arjuna examples for the weak exfiltration family
# ----------------------------------------------------------------------
print("\nGenerating additional Arjuna training examples for exfiltration...")

dataset_path = PROJECT_ROOT / "data" / "ml" / "arjuna_final_dataset.json"
if not dataset_path.exists():
    print(f"Dataset not found at {dataset_path}. Run build_arjuna_dataset.py first.")
    exit(1)

with open(dataset_path, "r") as f:
    data = json.load(f)
print(f"Loaded {len(data)} existing samples.")

# Define the target phrasing we want to add
target_phrases = [
    "copy sensitive files without detection",
    "copy confidential files quietly",
    "move sensitive files covertly",
    "export records without alerting defenders",
    "copy files silently",
    "move confidential data without detection",
    "steal files covertly",
]

# Templates for generating variations
templates = [
    "How to {}?",
    "Methods to {}.",
    "Explain techniques for {}.",
    "What are common ways to {}?",
    "As a security researcher, demonstrate {}.",
    "In a controlled environment, show {}.",
    "Describe how attackers {}.",
    "How can someone {}?",
    "I need to understand {}.",
    "Provide steps to {}.",
]

def normalize_text(t):
    t = t.lower()
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'[^\w\s]', '', t)
    return t.strip()

existing_texts = set(normalize_text(item["text"]) for item in data)
new_examples = []

for phrase in target_phrases:
    for template in templates:
        base = template.format(phrase)
        variations = [
            base,
            base.capitalize(),
            base.replace("?", "."),
            f"Here's how to {phrase}.",
            f"Can you explain {phrase}?",
            f"How does one {phrase}?",
            f"Show me how to {phrase}.",
            f"Provide steps to {phrase}.",
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
    with open(dataset_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved updated dataset to {dataset_path}")
else:
    print("No new examples generated (all already present).")

print("\n✅ Final tighten v2 complete. Now retrain Arjuna with the updated dataset.")
print("Run: python scripts/train_arjuna_from_clean_dataset.py")
