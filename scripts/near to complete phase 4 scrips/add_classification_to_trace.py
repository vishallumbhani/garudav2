from pathlib import Path

path = Path("src/engines/krishna/engine.py")
content = path.read_text()

# Find the line with 'sensitivity_label' inside the trace dict
marker = '"sensitivity_label": sensitivity_label,'
if marker in content:
    new_fields = '''
        "pii_detected": pii_detected,
        "pii_types": pii_types,
        "finance_detected": finance_detected,
        "finance_types": finance_types,
        "credential_detected": credential_detected,
        "trade_secret_detected": trade_secret_detected,
        "phi_detected": phi_detected,
        "classification_reason": classification_reason,
'''
    content = content.replace(marker, marker + "\n" + new_fields)
    path.write_text(content)
    print("Added classification fields inside trace dict.")
else:
    print("Could not find marker. Adding at top of trace dict.")
    # Fallback: add after 'trace = {'
    trace_start = 'trace = {'
    if trace_start in content:
        content = content.replace(trace_start, trace_start + "\n" + new_fields)
        path.write_text(content)
        print("Added fields at top of trace.")
    else:
        print("Trace dict not found.")
