#!/usr/bin/env python3
"""
Update scan_service to include all behavior fields, and ensure Krishna extracts them.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

def write_file(path, content):
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"Written: {file_path}")

# 1. Update scan_service.py to include new behavior fields
with open("src/services/scan_service.py", "r") as f:
    scan_content = f.read()

# Find the block where engine_results["behavior"] is set
# Look for: engine_results["behavior"] = {
pattern = '''        engine_results["behavior"] = {
            "engine": "behavior",
            "status": "ok",
            "escalation_factor": stats["escalation_factor"],
            "escalation_reason": stats["escalation_reason"],
            "request_count": stats["request_count"],
            "avg_risk": stats["avg_risk"],
            "max_risk": stats["max_risk"]
        }'''
new_block = '''        engine_results["behavior"] = {
            "engine": "behavior",
            "status": "ok",
            "escalation_factor": stats["escalation_factor"],
            "escalation_reason": stats["escalation_reason"],
            "request_count": stats["request_count"],
            "avg_risk": stats["avg_risk"],
            "max_risk": stats["max_risk"],
            "weighted_risk": stats["weighted_risk"],
            "classification": stats["classification"],
            "spike_detected": stats["spike_detected"],
            "last_risk": stats["last_risk"]
        }'''
if pattern in scan_content:
    scan_content = scan_content.replace(pattern, new_block)
    write_file("src/services/scan_service.py", scan_content)
    print("✅ Updated scan_service.py with new behavior fields.")
else:
    print("Pattern not found, check manually.")

# 2. Update Krishna to extract these fields (already done in upgrade script, but ensure)
with open("src/engines/krishna/engine.py", "r") as f:
    krishna = f.read()

# Ensure extraction lines are present
if "behavior_classification = behavior.get(" not in krishna:
    print("Krishna might need updates; but already done in previous script.")
    # We'll add them if missing
    # Find the line where behavior is extracted
    insert_after = "behavior = engine_results.get(\"behavior\", {})"
    new_lines = """
        behavior_classification = behavior.get(\"classification\", \"unknown\")
        behavior_spike = behavior.get(\"spike_detected\", False)
        behavior_weighted_risk = behavior.get(\"weighted_risk\", 0.0)
"""
    if insert_after in krishna:
        krishna = krishna.replace(insert_after, insert_after + new_lines)
        write_file("src/engines/krishna/engine.py", krishna)
        print("✅ Added behavior field extraction to Krishna.")
    else:
        print("Insert point not found in Krishna.")

print("✅ Behavior fields now propagated to trace.")
