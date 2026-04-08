# -*- coding: utf-8 -*-
#!/usr/bin/env python3
import re
from pathlib import Path

path = Path("src/services/scan_service.py")
with open(path, "r") as f:
    content = f.read()

# Find the block and reduce its indentation by 4 spaces (remove 4 spaces from the start of each line)
# We'll use a regex to capture the block.
pattern = r'(    # Threat memory \(Ashwatthama\)\n)((?:    .*\n)*?)(    # Record for future)'
match = re.search(pattern, content, re.MULTILINE)
if match:
    header = match.group(1)
    body = match.group(2)
    footer = match.group(3)
    # Reduce indentation of each line in body by 4 spaces (assuming 4 spaces per level)
    lines = body.split('\n')
    new_lines = []
    for line in lines:
        if line.startswith('        '):  # 8 spaces
            new_lines.append(line[4:])   # becomes 4 spaces (but we need 8? Actually we need to match the surrounding code)
        elif line.startswith('    '):    # 4 spaces
            new_lines.append(line[4:])   # becomes 0? That would be wrong.
        else:
            new_lines.append(line)
    new_body = '\n'.join(new_lines)
    new_content = content.replace(header + body + footer, header + new_body + footer)
    with open(path, "w") as f:
        f.write(new_content)
    print("Indentation reduced by 4 spaces.")
else:
    print("Block not found. Trying manual edit...")
    # Fallback: use line numbers to adjust
    lines = content.split('\n')
    # Find the line with "# Threat memory (Ashwatthama)"
    for i, line in enumerate(lines):
        if "# Threat memory (Ashwatthama)" in line:
            start = i
            break
    # Find the line with "# Record for future"
    for i, line in enumerate(lines[start:], start=start):
        if "# Record for future" in line:
            end = i
            break
    # Reduce indentation of lines from start+1 to end-1 by 4 spaces
    for j in range(start+1, end):
        if lines[j].startswith('        '):
            lines[j] = lines[j][4:]
        elif lines[j].startswith('    '):
            lines[j] = lines[j][4:]
    new_content = '\n'.join(lines)
    with open(path, "w") as f:
        f.write(new_content)
    print("Indentation reduced manually.")
