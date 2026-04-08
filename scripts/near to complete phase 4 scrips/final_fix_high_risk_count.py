#!/usr/bin/env python3
"""
Final fix: ensure session_high_risk_count is taken directly from behavior dict.
"""

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

# Read the file
with open("src/engines/krishna/engine.py", "r") as f:
    krishna = f.read()

# Remove any lines that assign behavior_high_risk_count
krishna = re.sub(r'\n\s*behavior_high_risk_count = behavior\.get\("high_risk_count", 0\)\n', '\n', krishna)

# Remove the duplicate line with behavior_high_risk_count in trace
krishna = re.sub(r'\n\s*"session_high_risk_count": behavior_high_risk_count,\n', '\n', krishna)

# Ensure the correct line exists and is the only one
# Add it if missing
if '"session_high_risk_count": behavior.get("high_risk_count", 0),' not in krishna:
    # Find the trace dict and insert the line after something like "session_reason"
    # For safety, we'll add it after "session_reason": line.
    pattern = r'("session_reason":.*?\n)'
    replacement = r'\1            "session_high_risk_count": behavior.get("high_risk_count", 0),\n'
    krishna = re.sub(pattern, replacement, krishna, count=1)

# Also add a debug print to verify
# Insert after behavior dict extraction
debug_line = "        print(f\"TRACE DEBUG: behavior.get('high_risk_count') = {behavior.get('high_risk_count')}\")"
if debug_line not in krishna:
    insert_after = "behavior = engine_results.get(\"behavior\", {})"
    krishna = krishna.replace(insert_after, insert_after + "\n        " + debug_line)

with open("src/engines/krishna/engine.py", "w") as f:
    f.write(krishna)

print("✅ Fixed session_high_risk_count trace.")
print("Restart server and test again.")
