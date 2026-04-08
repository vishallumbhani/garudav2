import re
from pathlib import Path

krishna_path = Path("src/engines/krishna/engine.py")
with open(krishna_path, "r") as f:
    content = f.read()

# Find where hanuman_info is extracted. If not present, add it.
if "hanuman_info = engine_results.get(\"hanuman\", {})" not in content:
    # Insert after some other extraction, e.g., after threat_memory
    marker = "threat_memory = engine_results.get(\"threat_memory\", {})"
    if marker in content:
        insert_code = '''
        hanuman_info = engine_results.get("hanuman", {})
        hanuman_content_kind = hanuman_info.get("content_kind", "unknown")
        hanuman_risk_hint = hanuman_info.get("risk_hint", "unknown")
        hanuman_complexity = hanuman_info.get("complexity", "unknown")
        hanuman_likely_family = hanuman_info.get("likely_family", "unknown")
        hanuman_language_hint = hanuman_info.get("language_hint", "")
        hanuman_log_type_hint = hanuman_info.get("log_type_hint", "")
        hanuman_document_type_hint = hanuman_info.get("document_type_hint", "")
        hanuman_line_count = hanuman_info.get("line_count", 0)
        hanuman_section_count = hanuman_info.get("section_count", 0)
        hanuman_has_code_blocks = hanuman_info.get("has_code_blocks", False)
        hanuman_has_stack_trace = hanuman_info.get("has_stack_trace", False)
        hanuman_has_secrets_pattern = hanuman_info.get("has_secrets_pattern", False)
        hanuman_summary = hanuman_info.get("summary", {})
'''
        content = content.replace(marker, marker + "\n" + insert_code)
        print("Added Hanuman extraction with defaults.")
    else:
        print("Could not find insertion point for Hanuman extraction.")
else:
    print("Hanuman extraction already present. Ensuring defaults for all fields...")
    # Add missing field definitions if needed.
    # We'll check if hanuman_language_hint is defined; if not, we'll add it.
    if "hanuman_language_hint = hanuman_info.get(\"language_hint\", \"\")" not in content:
        # Find the line where hanuman_info is extracted and add after it.
        # We'll do a simple replacement: find the line with hanuman_info.get and add after.
        pass

# Now ensure the trace fields are added with safe references.
# Find the trace dict building and insert the fields.
trace_fields = '''
        "hanuman_content_kind": hanuman_content_kind,
        "hanuman_risk_hint": hanuman_risk_hint,
        "hanuman_complexity": hanuman_complexity,
        "hanuman_likely_family": hanuman_likely_family,
        "hanuman_language_hint": hanuman_language_hint,
        "hanuman_log_type_hint": hanuman_log_type_hint,
        "hanuman_document_type_hint": hanuman_document_type_hint,
        "hanuman_line_count": hanuman_line_count,
        "hanuman_section_count": hanuman_section_count,
        "hanuman_has_code_blocks": hanuman_has_code_blocks,
        "hanuman_has_stack_trace": hanuman_has_stack_trace,
        "hanuman_has_secrets_pattern": hanuman_has_secrets_pattern,
        "hanuman_summary_chunk_count": hanuman_summary.get("chunk_count", 0),
        "hanuman_summary_suspicious_phrases": hanuman_summary.get("suspicious_phrases", []),
        "hanuman_summary_top_keywords": hanuman_summary.get("top_keywords", []),
'''
# Insert after a known trace field, e.g., after "decision_logic"
if '"decision_logic": decision_logic' in content:
    content = content.replace('"decision_logic": decision_logic', trace_fields + '"decision_logic": decision_logic')
    print("Added Hanuman fields to trace.")
else:
    # Alternative: insert after "deception_labels"
    if '"deception_labels": shakuni_labels,' in content:
        content = content.replace('"deception_labels": shakuni_labels,', trace_fields + '"deception_labels": shakuni_labels,')
        print("Added Hanuman fields after deception_labels.")
    else:
        print("Could not find insertion point. Manual edit may be needed.")

with open(krishna_path, "w") as f:
    f.write(content)
print("Krishna fixed.")
