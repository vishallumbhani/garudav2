import re
from pathlib import Path

hanuman_path = Path("src/engines/hanuman/engine.py")
with open(hanuman_path, "r") as f:
    content = f.read()

# Insert after file_hints definition
if "file_hints = {}" in content:
    # Add logic to set document_type_hint based on file metadata
    insert_code = '''
        # File-aware document type hint
        if request.file_metadata:
            ext = request.file_metadata.get("file_extension", "").lower()
            if ext in [".pdf", ".docx", ".txt", ".md"]:
                content_kind = "document"
                # Guess document type from filename or content
                name = request.file_metadata.get("original_name", "").lower()
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
            else:
                document_type_hint = None
        else:
            document_type_hint = None
'''
    content = content.replace("file_hints = {}", "file_hints = {}\n" + insert_code)
    print("Added file-aware document type hint.")
else:
    print("Could not find file_hints line.")

with open(hanuman_path, "w") as f:
    f.write(content)
