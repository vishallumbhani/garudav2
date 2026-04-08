#!/usr/bin/env python3
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

with open("src/services/behavior_service.py", "r") as f:
    lines = f.readlines()

# Find the return block and insert high_risk_count after request_count
for i, line in enumerate(lines):
    if "return {" in line:
        # Look for the line with "request_count": request_count,
        for j in range(i, len(lines)):
            if "request_count" in lines[j]:
                # Insert after that line
                indent = lines[j].split('"request_count"')[0]  # capture indentation
                new_line = f'{indent}            "high_risk_count": high_risk_count,\n'
                lines.insert(j+1, new_line)
                break
        break

with open("src/services/behavior_service.py", "w") as f:
    f.writelines(lines)
print("✅ Added high_risk_count to behavior return dict.")
