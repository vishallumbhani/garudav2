#!/usr/bin/env python3
"""
Add high_risk_count to the behavior service's returned dict.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

with open("src/services/behavior_service.py", "r") as f:
    content = f.read()

# Find the return statement and add high_risk_count.
# The return dict currently does not have it. We'll insert it.

# We'll look for the line that starts with "return {" and insert the key.
# We'll add it right after "request_count": request_count, for example.

# First, find the return block.
if "return {" in content:
    # We'll split at the return and insert the key.
    # We'll use a regex to add the line after request_count.
    import re
    pattern = r'(return \{[^}]*"request_count":\s*request_count,)'
    replacement = r'\1\n            "high_risk_count": high_risk_count,'
    new_content = re.sub(pattern, replacement, content)
    with open("src/services/behavior_service.py", "w") as f:
        f.write(new_content)
    print("✅ Added high_risk_count to behavior dict.")
else:
    print("Could not find return dict.")
