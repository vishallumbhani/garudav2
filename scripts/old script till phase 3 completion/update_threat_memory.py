# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""
Update scan_service.py and krishna/engine.py to use session-scoped and global threat memory.
"""

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

def main():
    # ------------------------------------------------------------------
    # 1. Update scan_service.py
    # ------------------------------------------------------------------
    scan_path = PROJECT_ROOT / "src" / "services" / "scan_service.py"
    with open(scan_path, "r") as f:
        scan_content = f.read()

    # Replace the threat memory block
    old_threat_block = r'''    # Threat memory \(Ashwatthama\)
    if request\.content_type == "text":
        threat_result = threat_memory\.get_memory_modifier\(request\.normalized_text\)
    else:
        threat_result = threat_memory\.get_memory_modifier\(request\.normalized_text, request\.content\)
    threat_result = fallback\.wrap_engine\("threat_memory", lambda req: threat_result, request\)
    engine_results\["threat_memory"\] = threat_result
    # Record for future
    threat_memory\.record_prompt\(request\.normalized_text\)
    if request\.content_type == "file":
        threat_memory\.record_file\(request\.content\)'''

    new_threat_block = '''    # Threat memory (Ashwatthama) - session + global
    if request.session_id:
        if request.content_type == "text":
            threat_result = threat_memory.get_memory_modifiers(request.session_id, request.normalized_text)
        else:
            threat_result = threat_memory.get_memory_modifiers(request.session_id, request.normalized_text, request.content)
        threat_result = fallback.wrap_engine("threat_memory", lambda req: threat_result, request)
        engine_results["threat_memory"] = threat_result
        # Record for future
        threat_memory.record_prompt(request.session_id, request.normalized_text)
        if request.content_type == "file":
            threat_memory.record_file(request.session_id, request.content)
    else:
        engine_results["threat_memory"] = {
            "engine": "threat_memory",
            "status": "ok",
            "session_modifier": 1.0,
            "session_reason": "No session",
            "global_modifier": 1.0,
            "global_reason": "No session",
        }'''

    if re.search(old_threat_block, scan_content, re.DOTALL):
        scan_content = re.sub(old_threat_block, new_threat_block, scan_content, flags=re.DOTALL)
        print("Updated threat memory block in scan_service.py")
    else:
        print("Could not find old threat memory block in scan_service.py. Skipping.")

    # Also ensure import of threat_memory is present (it should be, but just in case)
    if "from src.services.threat_memory import threat_memory" not in scan_content:
        # Add after other imports
        import_line = "from src.services.behavior_service import tracker"
        if import_line in scan_content:
            scan_content = scan_content.replace(import_line, import_line + "\nfrom src.services.threat_memory import threat_memory")
            print("Added threat_memory import.")
        else:
            print("Could not find behavior_service import line to add threat_memory import.")

    with open(scan_path, "w") as f:
        f.write(scan_content)

    # ------------------------------------------------------------------
    # 2. Update krishna/engine.py
    # ------------------------------------------------------------------
    krishna_path = PROJECT_ROOT / "src" / "engines" / "krishna" / "engine.py"
    with open(krishna_path, "r") as f:
        krishna_content = f.read()

    # Add extraction of threat_memory with both modifiers
    # Find where threat_memory is already extracted (if any) and replace
    old_threat_extract = r'(\s+)threat_memory = engine_results\.get\("threat_memory", {}\)\s+threat_memory_modifier = threat_memory\.get\("modifier", 1\.0\)\s+threat_memory_reason = threat_memory\.get\("reason", ""\)'
    new_threat_extract = r'\1threat_memory = engine_results.get("threat_memory", {})\n\1threat_session_modifier = threat_memory.get("session_modifier", 1.0)\n\1threat_global_modifier = threat_memory.get("global_modifier", 1.0)\n\1threat_session_reason = threat_memory.get("session_reason", "")\n\1threat_global_reason = threat_memory.get("global_reason", "")'
    if re.search(old_threat_extract, krishna_content, re.DOTALL):
        krishna_content = re.sub(old_threat_extract, new_threat_extract, krishna_content, flags=re.DOTALL)
        print("Updated threat memory extraction in Krishna.")
    else:
        # If not found, try to insert after behavior extraction
        behavior_line = r'(\s+)behavior = engine_results\.get\("behavior", {}\)'
        insert_after = r'\1behavior = engine_results.get("behavior", {})\n\1threat_memory = engine_results.get("threat_memory", {})\n\1threat_session_modifier = threat_memory.get("session_modifier", 1.0)\n\1threat_global_modifier = threat_memory.get("global_modifier", 1.0)\n\1threat_session_reason = threat_memory.get("session_reason", "")\n\1threat_global_reason = threat_memory.get("global_reason", "")'
        if re.search(behavior_line, krishna_content):
            krishna_content = re.sub(behavior_line, insert_after, krishna_content)
            print("Inserted threat memory extraction after behavior.")
        else:
            print("Could not find place to insert threat memory extraction.")

    # Update the modified_score line to include both modifiers
    old_score_line = r'(\s+)modified_score = base_weighted \* policy_modifier \* behavior_modifier \* threat_memory_modifier'
    new_score_line = r'\1modified_score = base_weighted * policy_modifier * behavior_modifier * threat_session_modifier * threat_global_modifier'
    if re.search(old_score_line, krishna_content):
        krishna_content = re.sub(old_score_line, new_score_line, krishna_content)
        print("Updated modified_score to include both threat modifiers.")
    else:
        # Maybe the line is different (no threat_memory_modifier yet)
        # Look for a line that has base_weighted * policy_modifier * behavior_modifier
        fallback_line = r'(\s+)modified_score = base_weighted \* policy_modifier \* behavior_modifier'
        if re.search(fallback_line, krishna_content):
            krishna_content = re.sub(fallback_line, r'\1modified_score = base_weighted * policy_modifier * behavior_modifier * threat_session_modifier * threat_global_modifier', krishna_content)
            print("Added threat modifiers to modified_score.")
        else:
            print("Could not find modified_score line. Manual update may be needed.")

    # Add the new fields to the trace dict
    # Find the trace dict and insert the new fields
    trace_insert = '''            "threat_session_modifier": round(threat_session_modifier, 2),
            "threat_session_reason": threat_session_reason,
            "threat_global_modifier": round(threat_global_modifier, 2),
            "threat_global_reason": threat_global_reason,
'''
    # Look for existing threat_memory fields and replace, or insert after behavior_reason
    if "threat_memory_modifier" in krishna_content:
        # Remove old lines
        krishna_content = re.sub(r'\s+"threat_memory_modifier":.*,\n', '', krishna_content)
        krishna_content = re.sub(r'\s+"threat_memory_reason":.*,\n', '', krishna_content)
    # Insert after "behavior_reason": behavior_reason,
    behavior_reason_line = '"behavior_reason": behavior_reason,'
    if behavior_reason_line in krishna_content:
        krishna_content = krishna_content.replace(behavior_reason_line, behavior_reason_line + "\n" + trace_insert)
        print("Inserted new threat memory fields into trace.")
    else:
        # Fallback: insert after "behavior_modifier": ...
        behavior_mod_line = '"behavior_modifier": round(behavior_modifier, 2),'
        if behavior_mod_line in krishna_content:
            krishna_content = krishna_content.replace(behavior_mod_line, behavior_mod_line + "\n" + trace_insert)
            print("Inserted new threat memory fields after behavior_modifier.")
        else:
            print("Could not find place to insert trace fields.")

    with open(krishna_path, "w") as f:
        f.write(krishna_content)

    print("\n✅ Threat memory updates applied. Restart server and test.")

if __name__ == "__main__":
    main()
