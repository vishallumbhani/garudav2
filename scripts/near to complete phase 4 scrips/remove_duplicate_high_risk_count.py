#!/usr/bin/env python3
"""
Remove duplicate session_high_risk_count entry in trace and ensure correct value.
"""

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

with open("src/engines/krishna/engine.py", "r") as f:
    krishna = f.read()

# Find lines that set session_high_risk_count
lines = krishna.split('\n')
new_lines = []
skip_next = False
for line in lines:
    # If we see the duplicate line that sets from behavior_high_risk_count, skip it
    if '"session_high_risk_count": behavior_high_risk_count' in line:
        # We'll skip this line because it overwrites the correct one
        continue
    new_lines.append(line)

# Write back
with open("src/engines/krishna/engine.py", "w") as f:
    f.write('\n'.join(new_lines))

print("✅ Removed duplicate session_high_risk_count line.")
print("Restart server and test again.")
