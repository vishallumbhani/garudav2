#!/usr/bin/env python3
"""
Remove duplicate session_high_risk_count in Krishna trace.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

with open("src/engines/krishna/engine.py", "r") as f:
    lines = f.readlines()

# Look for the line that contains "session_high_risk_count" and is using behavior_high_risk_count (line 151)
# We'll remove that line.
new_lines = []
for line in lines:
    if '"session_high_risk_count": behavior_high_risk_count' in line:
        continue  # skip this line
    new_lines.append(line)

with open("src/engines/krishna/engine.py", "w") as f:
    f.writelines(new_lines)

print("✅ Removed duplicate session_high_risk_count line.")
print("Restart server and test again.")
