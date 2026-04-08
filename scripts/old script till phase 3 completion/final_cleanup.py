#!/usr/bin/env python3
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

with open("src/engines/krishna/engine.py", "r") as f:
    lines = f.readlines()

# Remove any lines that start with 'print(f"TRACE DEBUG:' (including indentation)
new_lines = [line for line in lines if not 'TRACE DEBUG:' in line]

# Ensure the correct trace line is present
# We'll locate the trace dict and ensure "session_high_risk_count" line is correct
# But first, just write back the cleaned lines.
with open("src/engines/krishna/engine.py", "w") as f:
    f.writelines(new_lines)
print("Removed problematic debug line.")
