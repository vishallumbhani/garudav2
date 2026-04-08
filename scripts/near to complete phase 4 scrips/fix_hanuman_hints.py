import re
from pathlib import Path

path = Path("src/engines/hanuman/engine.py")
with open(path, "r") as f:
    content = f.read()

# Add document_type_hint for CSV
content = content.replace(
    'elif ext == ".csv":\n                content_kind = "structured_data"',
    'elif ext == ".csv":\n                content_kind = "structured_data"\n                document_type_hint = "tabular"'
)

# Add document_type_hint for JSON
content = content.replace(
    'elif ext == ".json":\n                content_kind = "structured_data"',
    'elif ext == ".json":\n                content_kind = "structured_data"\n                document_type_hint = "json_config"'
)

# Ensure log_type_hint is set for .log (already does, but just in case)
content = content.replace(
    'elif ext == ".log":\n                content_kind = "log"\n                log_type_hint = "system"',
    'elif ext == ".log":\n                content_kind = "log"\n                log_type_hint = "system"'
)

with open(path, "w") as f:
    f.write(content)
print("Hanuman hints fixed.")
