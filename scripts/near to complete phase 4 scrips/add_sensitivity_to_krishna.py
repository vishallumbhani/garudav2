from pathlib import Path

krishna_path = Path("src/engines/krishna/engine.py")
content = krishna_path.read_text()

# Extract classification info
insert_after = "threat_memory = engine_results.get(\"threat_memory\", {})"
new_extract = '''
        classification = engine_results.get("data_classification", {})
        sensitivity_label = classification.get("sensitivity_label", "LOW")
        data_categories = classification.get("data_categories", [])
'''
if insert_after in content:
    content = content.replace(insert_after, insert_after + "\n" + new_extract)
    print("Added classification extraction.")

# Add decision floor
# Insert before the existing session floor or after category floor
marker = "# Session-based decision floor"
new_floor = '''
        # Sensitivity-based decision floor
        if sensitivity_label == "CRITICAL":
            decision = "block"
            decision_logic += " (sensitivity: CRITICAL -> block)"
        elif sensitivity_label == "HIGH" and decision != "block":
            decision = "challenge"
            decision_logic += " (sensitivity: HIGH -> challenge)"
        elif sensitivity_label == "MEDIUM" and decision not in ["block", "challenge"]:
            decision = "monitor"
            decision_logic += " (sensitivity: MEDIUM -> monitor)"
'''
if marker in content:
    content = content.replace(marker, new_floor + "\n\n" + marker)
    print("Added sensitivity floor.")

# Add trace fields
trace_insert = '        "sensitivity_label": sensitivity_label,\n        "data_categories": data_categories,\n'
# Insert after a known trace field, e.g., "deception_labels"
if '"deception_labels": shakuni_labels,' in content:
    content = content.replace('"deception_labels": shakuni_labels,', '"deception_labels": shakuni_labels,\n' + trace_insert)
    print("Added sensitivity fields to trace.")
else:
    print("Could not add trace fields.")

krishna_path.write_text(content)
