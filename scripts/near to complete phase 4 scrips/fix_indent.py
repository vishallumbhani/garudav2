# -*- coding: utf-8 -*-
import re
from pathlib import Path

path = Path("src/services/scan_service.py")
with open(path, "r") as f:
    lines = f.readlines()

# Find the lines that contain the threat memory block.
# We'll search for the line starting with "# Threat memory (Ashwatthama)"
start_idx = None
for i, line in enumerate(lines):
    if "# Threat memory (Ashwatthama)" in line:
        start_idx = i
        break

if start_idx is None:
    print("Could not find the block.")
    exit(1)

# Now we need to find the end of the block. It ends at the line that contains "# Record for future" (or the next line that starts without indentation).
# We'll scan until we find a line that is less indented than the block start.
# The block start line is likely indented with 8 spaces (since it's inside the function).
# Let's check the indentation of the start line.
start_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
print(f"Block starts at line {start_idx+1} with indent {start_indent}")

# Find the end: the first line after start_idx that has indent <= start_indent (excluding empty lines)
end_idx = start_idx
for i in range(start_idx+1, len(lines)):
    if lines[i].strip() == "":
        continue
    current_indent = len(lines[i]) - len(lines[i].lstrip())
    if current_indent <= start_indent:
        end_idx = i-1
        break
else:
    end_idx = len(lines)-1

print(f"Block ends at line {end_idx+1}")

# Now reduce the indentation of all lines from start_idx to end_idx by 4 spaces
for i in range(start_idx, end_idx+1):
    if lines[i].startswith(' ' * 8):
        lines[i] = lines[i][4:]
    elif lines[i].startswith(' ' * 4):
        # Maybe some lines are already correct
        pass

# Write back
with open(path, "w") as f:
    f.writelines(lines)

print("Indentation fixed.")
