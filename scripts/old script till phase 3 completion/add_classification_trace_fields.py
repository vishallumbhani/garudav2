from pathlib import Path

path = Path("src/engines/krishna/engine.py")
content = path.read_text()

# Check if the fields are already there
if 'pii_detected' in content:
    print("Fields already present.")
    exit(0)

# Find the trace dict and insert after the opening brace
trace_start = 'trace = {'
if trace_start in content:
    insert_fields = '''
        "pii_detected": pii_detected,
        "pii_types": pii_types,
        "finance_detected": finance_detected,
        "finance_types": finance_types,
        "credential_detected": credential_detected,
        "trade_secret_detected": trade_secret_detected,
        "phi_detected": phi_detected,
        "classification_reason": classification_reason,
'''
    content = content.replace(trace_start, trace_start + insert_fields)
    path.write_text(content)
    print("Added classification trace fields.")
else:
    print("Could not find trace = {")
