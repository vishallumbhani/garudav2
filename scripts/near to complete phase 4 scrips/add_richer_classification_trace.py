from pathlib import Path

path = Path("src/engines/krishna/engine.py")
content = path.read_text()

# Add extraction of richer classification fields
if "classification = engine_results.get(\"data_classification\", {})" in content:
    # Replace with more detailed extraction
    old_extract = "classification = engine_results.get(\"data_classification\", {})"
    new_extract = '''classification = engine_results.get("data_classification", {})
        pii_detected = classification.get("pii_detected", False)
        pii_types = classification.get("pii_types", [])
        finance_detected = classification.get("finance_detected", False)
        finance_types = classification.get("finance_types", [])
        credential_detected = classification.get("credential_detected", False)
        trade_secret_detected = classification.get("trade_secret_detected", False)
        phi_detected = classification.get("phi_detected", False)
        classification_reason = classification.get("classification_reason", "")'''
    content = content.replace(old_extract, new_extract)
    print("Updated classification extraction.")

# Add fields to trace
trace_fields = '''        "pii_detected": pii_detected,
        "pii_types": pii_types,
        "finance_detected": finance_detected,
        "finance_types": finance_types,
        "credential_detected": credential_detected,
        "trade_secret_detected": trade_secret_detected,
        "phi_detected": phi_detected,
        "classification_reason": classification_reason,
'''
# Insert after the existing sensitivity fields
if '"sensitivity_label": sensitivity_label,' in content:
    content = content.replace('"sensitivity_label": sensitivity_label,', '"sensitivity_label": sensitivity_label,\n' + trace_fields)
    print("Added richer classification fields to trace.")
else:
    print("Could not find insertion point. Adding at top of trace.")
    content = content.replace('trace = {', 'trace = {\n' + trace_fields)
    print("Added fields at top of trace.")

path.write_text(content)
print("Krishna updated with richer classification trace fields.")
