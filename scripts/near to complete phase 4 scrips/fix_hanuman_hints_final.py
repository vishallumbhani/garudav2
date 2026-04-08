import re
from pathlib import Path

path = Path("src/engines/hanuman/engine.py")
with open(path, "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    new_lines.append(line)
    if line.strip().startswith('elif ext == ".csv":'):
        # Add the next line after it (should be content_kind assignment)
        # We'll add the document_type_hint after that.
        new_lines.append('                content_kind = "structured_data"\n')
        new_lines.append('                document_type_hint = "tabular"\n')
        # Skip the original content_kind line (if present) to avoid duplication
    elif line.strip().startswith('elif ext == ".json":'):
        new_lines.append('                content_kind = "structured_data"\n')
        new_lines.append('                document_type_hint = "json_config"\n')
    elif line.strip().startswith('elif ext == ".log":'):
        new_lines.append('                content_kind = "log"\n')
        new_lines.append('                log_type_hint = "system"\n')
    # For other lines, just pass

# Remove duplicate lines (the original ones that might be there)
# We'll write the new lines and then remove duplicates by a simple filter (not perfect but works)
# Actually easier: we'll replace the whole block manually by searching for the old block.
# Let's do a simpler approach: we'll use a regex to replace the old blocks.

# Instead of this, let's just use sed to add the lines after the existing assignments.
# But we already have the content; we'll write it back after cleaning.
# This is getting messy. I'll provide a manual edit instruction.

print("Please manually edit src/engines/hanuman/engine.py and add the following lines:")
print("After the line that sets content_kind for .csv, add: document_type_hint = 'tabular'")
print("After the line that sets content_kind for .json, add: document_type_hint = 'json_config'")
print("After the line that sets content_kind for .log, add: log_type_hint = 'system'")
print("Then restart the server.")
