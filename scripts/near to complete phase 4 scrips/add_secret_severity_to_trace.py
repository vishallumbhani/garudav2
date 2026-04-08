from pathlib import Path

path = Path("src/engines/krishna/engine.py")
content = path.read_text()

# Add secret_severity to trace
insert_after = '"hanuman_detected_secrets": hanuman_info.get("detected_secrets", []),'
new_field = '        "secret_severity": hanuman_info.get("secret_severity"),'
if insert_after in content:
    content = content.replace(insert_after, insert_after + "\n" + new_field)
    path.write_text(content)
    print("Added secret_severity to trace.")
else:
    print("Could not find insertion point. Trying alternative.")
    # Fallback: add after hanuman_detected_dangerous_functions
    insert_after2 = '"hanuman_detected_dangerous_functions": hanuman_info.get("detected_dangerous_functions", []),'
    if insert_after2 in content:
        content = content.replace(insert_after2, insert_after2 + "\n" + new_field)
        path.write_text(content)
        print("Added secret_severity after dangerous functions.")
    else:
        print("Manual edit needed.")
