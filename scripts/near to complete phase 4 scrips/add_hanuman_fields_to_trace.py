import re
from pathlib import Path

krishna_path = Path("src/engines/krishna/engine.py")
with open(krishna_path, "r") as f:
    content = f.read()

# Add extraction of Hanuman fields from engine_results
if "hanuman_info = engine_results.get(\"hanuman\", {})" not in content:
    # Insert after similar extractions
    marker = "threat_memory = engine_results.get(\"threat_memory\", {})"
    if marker in content:
        insert_code = '''
        hanuman_info = engine_results.get("hanuman", {})
        hanuman_content_kind = hanuman_info.get("content_kind", "unknown")
        hanuman_risk_hint = hanuman_info.get("risk_hint", "unknown")
        hanuman_complexity = hanuman_info.get("complexity", "unknown")
        hanuman_likely_family = hanuman_info.get("likely_family", "unknown")
'''
        content = content.replace(marker, marker + "\n" + insert_code)
        print("Added Hanuman field extraction.")
    else:
        print("Marker not found.")

# Add fields to trace
trace_fields = '''
        "hanuman_content_kind": hanuman_content_kind,
        "hanuman_risk_hint": hanuman_risk_hint,
        "hanuman_complexity": hanuman_complexity,
        "hanuman_likely_family": hanuman_likely_family,
'''
# Find where to insert (e.g., after "deception_labels")
if '"deception_labels": shakuni_labels,' in content:
    content = content.replace('"deception_labels": shakuni_labels,', '"deception_labels": shakuni_labels,\n' + trace_fields)
    print("Added Hanuman fields to trace.")
else:
    print("Could not find deception_labels line.")

with open(krishna_path, "w") as f:
    f.write(content)
print("Krishna updated to include Hanuman fields in trace.")
