#!/usr/bin/env python3
"""
Fix Krishna's base_weighted_score calculation and session_high_risk_count.
"""

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

def write_file(path, content):
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"Written: {file_path}")

# 1. Fix Krishna: recompute base_weighted_score using the same scores used in the trace
with open("src/engines/krishna/engine.py", "r") as f:
    krishna = f.read()

# Find the part where base_weighted is computed. It currently uses the variables:
# bhishma_score, hanuman_score, shakuni_score, arjuna_score
# We'll ensure that after extracting them, we compute base_weighted correctly.
# The issue might be that one of these scores is being modified later (e.g., by a modifier) before the trace.
# To be safe, we'll compute base_weighted immediately after extracting all scores and use that for the trace.
# We'll also ensure that the trace uses that same variable.

# Insert a new variable `base_for_trace` after extracting all scores.
# We'll find the line where arjuna_score is extracted.
if "arjuna_score = arjuna.get(\"score\", 0.5)" in krishna:
    # Insert after that line:
    insert_point = "arjuna_score = arjuna.get(\"score\", 0.5)"
    new_lines = f"""
        # Compute base weighted score for trace (before modifiers)
        base_for_trace = (self.weights["bhishma"] * bhishma_score +
                          self.weights["hanuman"] * hanuman_score +
                          self.weights["shakuni"] * shakuni_score +
                          self.weights["arjuna"] * arjuna_score)
        print(f"DEBUG: base_for_trace = {{base_for_trace}}")
"""
    krishna = krishna.replace(insert_point, insert_point + new_lines)

# Now find where the trace uses "base_weighted_score" and replace with base_for_trace
# The current line might be:
#   "base_weighted_score": round(base_weighted, 3),
# We'll replace base_weighted with base_for_trace.
pattern = r'"base_weighted_score": round\(base_weighted, 3\),'
replacement = '"base_weighted_score": round(base_for_trace, 3),'
krishna = re.sub(pattern, replacement, krishna)

write_file("src/engines/krishna/engine.py", krishna)
print("✅ Fixed Krishna base_weighted_score calculation.")

# 2. Fix session_high_risk_count: ensure behavior service returns the correct value and Krishna uses it.
with open("src/services/behavior_service.py", "r") as f:
    behavior = f.read()

# The behavior service already returns high_risk_count. The issue might be that in Krishna, we are using
# behavior.get("high_risk_count", 0) but the key might be different. Let's add a debug print to see what behavior contains.
# We'll modify Krishna to print the behavior dict.
with open("src/engines/krishna/engine.py", "r") as f:
    krishna = f.read()

# Insert a debug print before building trace to see behavior dict.
debug_line = 'print(f"DEBUG: behavior dict = {behavior}")'
if debug_line not in krishna:
    # Insert after behavior is extracted
    insert_after = "behavior = engine_results.get(\"behavior\", {})"
    krishna = krishna.replace(insert_after, insert_after + "\n        " + debug_line)
    write_file("src/engines/krishna/engine.py", krishna)
    print("✅ Added debug print for behavior dict.")

print("\n✅ Fixes applied. Restart server and run test, then share the debug output.")
