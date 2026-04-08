#!/usr/bin/env python3
"""
Add high_risk_count to the behavior service's return dict.
"""

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

with open("src/services/behavior_service.py", "r") as f:
    content = f.read()

# Find the return block. It's a multi-line dict literal.
# We'll locate the line that contains "request_count": request_count,
# and insert the new line after it.
pattern = r'("request_count": request_count,)'
replacement = r'\1\n            "high_risk_count": high_risk_count,'
new_content = re.sub(pattern, replacement, content)

with open("src/services/behavior_service.py", "w") as f:
    f.write(new_content)

print("Added high_risk_count to behavior dict.")
