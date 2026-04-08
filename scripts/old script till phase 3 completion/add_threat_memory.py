# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Add Ashwatthama threat memory to the pipeline.
"""

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

# ----------------------------------------------------------------------
# 1. Patch scan_service.py to include threat memory
# ----------------------------------------------------------------------
scan_path = PROJECT_ROOT / "src" / "services" / "scan_service.py"
with open(scan_path, "r") as f:
    scan_content = f.read()

# Add import if not present
if "from src.services.threat_memory import threat_memory" not in scan_content:
    # Find where other imports are (e.g., after from src.services.behavior_service import tracker)
    import_line = "from src.services.behavior_service import tracker"
    if import_line in scan_content:
        scan_content = scan_content.replace(import_line, f"{import_line}\nfrom src.services.threat_memory import threat_memory")
    else:
        print("Warning: Could not find import line for behavior_service. Adding at top.")
        scan_content = "from src.services.threat_memory import threat_memory\n" + scan_content

# Insert the threat memory call after behavior tracking.
# Look for the block where behavior results are added.
# We'll add after:
#   engine_results["behavior"] = behavior_result
behavior_marker = 'engine_results["behavior"] = behavior_result'
if behavior_marker in scan_content:
    insert_after = behavior_marker + "\n"
    new_lines = '''
    # Threat memory (Ashwatthama)
    if request.content_type == "text":
        threat_result = threat_memory.get_memory_modifier(request.normalized_text)
    else:
        threat_result = threat_memory.get_memory_modifier(request.normalized_text, request.content)
    threat_result = fallback.wrap_engine("threat_memory", lambda req: threat_result, request)
    engine_results["threat_memory"] = threat_result
    # Record for future
    threat_memory.record_prompt(request.normalized_text)
    if request.content_type == "file":
        threat_memory.record_file(request.content)
'''
    scan_content = scan_content.replace(insert_after, insert_after + new_lines)
    with open(scan_path, "w") as f:
        f.write(scan_content)
    print("Updated scan_service.py with threat memory.")
else:
    print("Could not find behavior marker in scan_service.py")

# ----------------------------------------------------------------------
# 2. Update Krishna to use threat memory modifier
# ----------------------------------------------------------------------
krishna_path = PROJECT_ROOT / "src" / "engines" / "krishna" / "engine.py"
with open(krishna_path, "r") as f:
    krishna_content = f.read()

# Add extraction of threat_memory
if "threat_memory = engine_results.get(\"threat_memory\", {})" not in krishna_content:
    # Insert after behavior extraction
    insert_after = "behavior = engine_results.get(\"behavior\", {})"
    new_lines = "\n        threat_memory = engine_results.get(\"threat_memory\", {})"
    krishna_content = krishna_content.replace(insert_after, insert_after + new_lines)

# Add threat_memory modifier to the weighted score calculation
# Find where modified_score is computed (after policy_modifier and behavior_modifier)
# It currently has: modified_score = base_weighted * policy_modifier * behavior_modifier
# We'll insert threat_memory modifier.
old_line = "modified_score = base_weighted * policy_modifier * behavior_modifier"
if old_line in krishna_content:
    new_line = "        threat_memory_modifier = threat_memory.get(\"modifier\", 1.0)\n        threat_memory_reason = threat_memory.get(\"reason\", \"\")\n        modified_score = base_weighted * policy_modifier * behavior_modifier * threat_memory_modifier"
    krishna_content = krishna_content.replace(old_line, new_line)
    # Also add threat_memory_modifier to trace
    # Insert after behavior_reason in trace dict
    trace_insert = '            "threat_memory_modifier": round(threat_memory_modifier, 2),\n            "threat_memory_reason": threat_memory_reason,\n'
    # Find where behavior_reason is added to trace
    behavior_reason_line = '"behavior_reason": behavior_reason,'
    if behavior_reason_line in krishna_content:
        krishna_content = krishna_content.replace(behavior_reason_line, behavior_reason_line + "\n" + trace_insert)
    else:
        # Fallback: insert after behavior_modifier line
        behavior_modifier_line = '"behavior_modifier": round(behavior_modifier, 2),'
        if behavior_modifier_line in krishna_content:
            krishna_content = krishna_content.replace(behavior_modifier_line, behavior_modifier_line + "\n" + trace_insert)
    with open(krishna_path, "w") as f:
        f.write(krishna_content)
    print("Updated Krishna with threat memory modifier.")
else:
    print("Could not find modified_score line in Krishna.")

print("\n✅ Ashwatthama threat memory added.")
print("Restart server and test.")
