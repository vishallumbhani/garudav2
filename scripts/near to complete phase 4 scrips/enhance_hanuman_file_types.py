import re
from pathlib import Path

hanuman_path = Path("src/engines/hanuman/engine.py")
with open(hanuman_path, "r") as f:
    content = f.read()

# Find the section where content_kind is determined (around line 100)
# We'll replace the file‑aware block with a more comprehensive version.

# Look for the existing file‑aware block (if any) or insert a new one after file_hints.
# We'll search for a line that sets file_hints = {} and add our logic after it.

insert_point = "file_hints = {}"
new_block = '''
        # File-aware content kind and hints
        if request.file_metadata:
            ext = request.file_metadata.get("file_extension", "").lower()
            name = request.file_metadata.get("original_name", "").lower()
            if ext in [".pdf", ".docx", ".txt", ".md"]:
                content_kind = "document"
                if "policy" in name or "procedure" in name:
                    document_type_hint = "policy"
                elif "report" in name or "analysis" in name:
                    document_type_hint = "report"
                elif "manual" in name or "guide" in name:
                    document_type_hint = "manual"
                elif "spec" in name or "design" in name:
                    document_type_hint = "spec"
                else:
                    document_type_hint = "general_doc"
            elif ext == ".csv":
                content_kind = "structured_data"
                document_type_hint = "tabular"
            elif ext == ".json":
                content_kind = "structured_data"
                document_type_hint = "json_config"
            elif ext == ".log":
                content_kind = "log"
                log_type_hint = "system"
            else:
                content_kind = "text"
                document_type_hint = None
                log_type_hint = None
        else:
            document_type_hint = None
            log_type_hint = None
'''

if insert_point in content:
    content = content.replace(insert_point, insert_point + new_block)
    print("Inserted enhanced file-aware block.")
else:
    print("Could not find file_hints line. Trying alternative insertion.")
    # Fallback: insert after the line that sets risk_hint (somewhere after)
    risk_hint_line = 'risk_hint = "low"'
    if risk_hint_line in content:
        content = content.replace(risk_hint_line, risk_hint_line + new_block)
        print("Inserted after risk_hint line.")
    else:
        print("No suitable insertion point found. Manual edit may be needed.")

with open(hanuman_path, "w") as f:
    f.write(content)
print("Hanuman file type detection enhanced.")
