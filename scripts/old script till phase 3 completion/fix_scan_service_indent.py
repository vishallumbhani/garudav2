import re
from pathlib import Path

path = Path("src/services/scan_service.py")
content = path.read_text()

# Find the line with the indentation error
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'engine_results["yudhishthira"] = yudhishthira_result' in line:
        # Look at the previous line to get its indentation
        if i > 0:
            prev_line = lines[i-1]
            # Count leading spaces
            indent = len(prev_line) - len(prev_line.lstrip())
            lines[i] = ' ' * indent + line.lstrip()
            break
content = '\n'.join(lines)
path.write_text(content)
print("Fixed indentation.")
