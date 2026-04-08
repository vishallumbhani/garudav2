import re
from pathlib import Path

krishna_path = Path("src/engines/krishna/engine.py")
with open(krishna_path, "r") as f:
    content = f.read()

# Add extraction of new Hanuman fields
if "hanuman_info = engine_results.get(\"hanuman\", {})" not in content:
    # Insert after existing hanuman extraction
    marker = "hanuman_info = engine_results.get(\"hanuman\", {})"
    if marker in content:
        insert_code = '''
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
        print("Added enhanced Hanuman field extraction.")
    else:
        print("Marker not found. Please ensure hanuman_info is already extracted.")
else:
    print("Hanuman extraction already present. Adding new fields...")
    # We'll still add the new lines after the existing ones if needed.

# Add fields to trace
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
# Insert after existing Hanuman fields in trace (e.g., after "hanuman_likely_family")
if '"hanuman_likely_family": hanuman_likely_family,' in content:
    content = content.replace('"hanuman_likely_family": hanuman_likely_family,', '"hanuman_likely_family": hanuman_likely_family,\n' + trace_fields)
    print("Added enhanced Hanuman fields to trace.")
else:
    print("Could not find insertion point. Manual edit may be needed.")

with open(krishna_path, "w") as f:
    f.write(content)
print("Krishna updated.")
