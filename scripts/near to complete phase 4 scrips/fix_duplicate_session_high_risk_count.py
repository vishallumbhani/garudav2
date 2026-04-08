#!/usr/bin/env python3
"""
Remove duplicate session_high_risk_count line and ensure the correct one is used.
"""

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

with open("src/engines/krishna/engine.py", "r") as f:
    krishna = f.read()

# There are two lines with "session_high_risk_count". We'll remove the one that uses a variable.
# The line we want to keep is: '"session_high_risk_count": behavior.get("high_risk_count", 0),'
# The other line is: '"session_high_risk_count": behavior_high_risk_count,'
# We'll remove the latter.

# Find the pattern for the unwanted line
pattern = r'^\s*"session_high_risk_count":\s*behavior_high_risk_count,\s*$'
# Replace with empty string (remove it)
krishna = re.sub(pattern, '', krishna, flags=re.MULTILINE)

# Also ensure there's no stray comma from the removal (if needed)
# The line removal might leave an extra comma if it's inside a dict. We'll do a quick check for two consecutive commas.
krishna = re.sub(r',\s*,', ',', krishna)

with open("src/engines/krishna/engine.py", "w") as f:
    f.write(krishna)

print("✅ Removed duplicate session_high_risk_count line.")
print("Restart server and test again.")
