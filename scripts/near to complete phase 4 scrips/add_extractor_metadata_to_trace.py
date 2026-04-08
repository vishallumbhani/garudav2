import re
from pathlib import Path

krishna_path = Path("src/engines/krishna/engine.py")
with open(krishna_path, "r") as f:
    content = f.read()

# Add extraction of file_metadata from request
# We need to pass request to Krishna? It's already there.
# We'll add the fields to the trace.
# Since the request is available in Krishna.run, we can access request.file_metadata.

# Insert after hanuman fields in trace
insert_fields = '''
        # File extractor metadata
        "file_metadata": request.file_metadata if hasattr(request, 'file_metadata') else None,
'''
# Find a good place, e.g., after hanuman_summary_top_keywords
if "hanuman_summary_top_keywords" in content:
    content = content.replace('"hanuman_summary_top_keywords": hanuman_summary.get("top_keywords", []),',
                              '"hanuman_summary_top_keywords": hanuman_summary.get("top_keywords", []),\n' + insert_fields)
    print("Added extractor metadata to trace.")
else:
    print("Could not find insertion point.")

with open(krishna_path, "w") as f:
    f.write(content)
