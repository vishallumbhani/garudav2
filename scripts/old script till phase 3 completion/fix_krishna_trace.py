from pathlib import Path
import re

path = Path("src/engines/krishna/engine.py")
content = path.read_text()

# Remove any lines that start with "pii_detected": etc. that are not inside the trace dict
# We'll assume they are at the end of the file or somewhere. Let's just search for them and delete.
lines = content.split('\n')
new_lines = []
in_trace = False
brace_count = 0
for line in lines:
    # Check if we are inside the trace dict
    if 'trace = {' in line:
        in_trace = True
        brace_count += line.count('{') - line.count('}')
    if in_trace:
        brace_count += line.count('{') - line.count('}')
        if brace_count == 0 and '}' in line:
            in_trace = False
        # If we are inside trace, keep all lines
        new_lines.append(line)
    else:
        # Outside trace: skip lines that look like classification fields
        if re.match(r'\s*"pii_detected":', line) or \
           re.match(r'\s*"pii_types":', line) or \
           re.match(r'\s*"finance_detected":', line) or \
           re.match(r'\s*"finance_types":', line) or \
           re.match(r'\s*"credential_detected":', line) or \
           re.match(r'\s*"trade_secret_detected":', line) or \
           re.match(r'\s*"phi_detected":', line) or \
           re.match(r'\s*"classification_reason":', line):
            continue
        else:
            new_lines.append(line)

content = '\n'.join(new_lines)

# Now add the fields inside the trace dict after 'sensitivity_label'
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
    print("Marker not found.")
