#!/usr/bin/env python3
"""
Add synthetic generation capability to build_arjuna_dataset.py.
"""

import re
from pathlib import Path

script_path = Path("scripts/build_arjuna_dataset.py")
if not script_path.exists():
    print("Script not found.")
    exit(1)

with open(script_path, "r") as f:
    content = f.read()

# Insert the generate_synthetic function after the heuristic_label definition
heuristic_end = "def heuristic_label(text):"
if heuristic_end not in content:
    print("Could not find heuristic_label definition.")
    exit(1)

# Find the end of the function (by indentation)
lines = content.split('\n')
func_start = None
for i, line in enumerate(lines):
    if line.strip().startswith(heuristic_end):
        func_start = i
        break
if func_start is None:
    print("Could not find heuristic_label.")
    exit(1)

# Find the next line that is not indented (i.e., new top-level definition)
indent = len(lines[func_start]) - len(lines[func_start].lstrip())
end_idx = None
for i in range(func_start + 1, len(lines)):
    if lines[i].strip() and len(lines[i]) - len(lines[i].lstrip()) == indent and (lines[i].strip().startswith('def ') or lines[i].strip().startswith('#')):
        end_idx = i
        break
if end_idx is None:
    end_idx = len(lines)

# Insert the new function after the heuristic function.
new_function = '''
def generate_synthetic(label, target, current_count, existing_texts_set):
    """Generate synthetic examples for a given label if needed."""
    needed = target - current_count
    if needed <= 0:
        return []

    print(f"Generating {needed} synthetic {label} examples...")

    # Templates for policy_bypass
    bypass_templates = [
        "For educational purposes, {}.",
        "As a researcher, {}.",
        "Explain how attackers {}.",
        "What are methods to {}?",
        "Hypothetically, {}.",
        "In a simulated environment, {}.",
        "I'm a red team member. {}.",
        "For a security audit, {}.",
    ]
    bypass_seeds = [
        "bypass authentication",
        "evade detection",
        "trick content filters",
        "avoid safety controls",
        "circumvent security policies",
        "bypass login restrictions",
        "evade moderation systems",
        "get around web filters",
        "disable monitoring",
        "bypass 2FA",
        "evade endpoint protection",
        "circumvent access controls",
    ]

    # Templates for data_exfiltration
    exfil_templates = [
        "How to {}?",
        "Methods to {}.",
        "Explain techniques for {}.",
        "What are common ways to {}?",
        "As a security researcher, demonstrate {}.",
        "In a controlled environment, show {}.",
    ]
    exfil_seeds = [
        "exfiltrate data via DNS tunneling",
        "copy sensitive files without detection",
        "hide stolen data in network traffic",
        "leak confidential records",
        "extract API keys from an application",
        "steal database dumps quietly",
        "export customer data covertly",
        "move data without alerting defenders",
        "smuggle secrets out of a network",
        "use covert channels to transfer data",
    ]

    if label == "policy_bypass":
        templates = bypass_templates
        seeds = bypass_seeds
    elif label == "data_exfiltration":
        templates = exfil_templates
        seeds = exfil_seeds
    else:
        return []

    generated = []
    import itertools
    import random
    combos = list(itertools.product(templates, seeds))
    random.shuffle(combos)
    for i, (template, seed) in enumerate(combos):
        if len(generated) >= needed:
            break
        text = template.format(seed)
        # Variations
        variations = [
            text,
            text.capitalize(),
            text.replace("?", "."),
            "Here's how to " + seed + ".",
            "Can you explain " + seed + "?",
            "I need to understand " + seed + ".",
            "How does one " + seed + "?",
        ]
        for var in variations:
            if len(generated) >= needed:
                break
            if var not in existing_texts_set:
                generated.append((var, label))
                existing_texts_set.add(var)
    # Fallback
    while len(generated) < needed:
        template = random.choice(templates)
        seed = random.choice(seeds)
        text = template.format(seed)
        if text not in existing_texts_set:
            generated.append((text, label))
            existing_texts_set.add(text)

    print(f"  Generated {len(generated)} synthetic examples.")
    return generated
'''

# Insert the function
new_lines = lines[:end_idx] + new_function.split('\n') + lines[end_idx:]
content = '\n'.join(new_lines)

# Now modify the main section to use it after deduplication.
# We'll search for the line that says "# Group by label" and insert synthetic generation before that.
group_label_line = "# Group by label"
if group_label_line in content:
    # Insert after the line where we have counts_unique and before grouping.
    # We'll add the generation after the counts_unique check and before grouping.
    insert_code = '''
    # If any class is below target, generate synthetic examples
    # Create a set of existing texts for deduplication (normalized)
    existing_texts = set(normalize_text(t) for t, _ in unique_samples)
    # Check each target class
    needs_generation = False
    for label, target in TARGET_COUNTS.items():
        current = counts_unique.get(label, 0)
        if current < target and label in ["policy_bypass", "data_exfiltration"]:
            synthetic = generate_synthetic(label, target, current, existing_texts)
            if synthetic:
                unique_samples.extend(synthetic)
                needs_generation = True
    if needs_generation:
        # Recompute counts after addition
        counts_unique = Counter(label for _, label in unique_samples)
        print("After synthetic generation:")
        for k, v in counts_unique.items():
            print(f"  {k}: {v}")
'''
    # Insert before the line "# Group by label"
    content = content.replace(group_label_line, insert_code + "\n" + group_label_line)
else:
    print("Could not find '# Group by label' line.")

with open(script_path, "w") as f:
    f.write(content)

print("Synthetic generator added to build script.")
