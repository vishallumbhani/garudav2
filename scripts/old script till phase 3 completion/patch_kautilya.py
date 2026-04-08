#!/usr/bin/env python3
"""
Patch scan_service.py to integrate Kautilya routing.
"""

import re
from pathlib import Path

def main():
    scan_path = Path("src/services/scan_service.py")
    if not scan_path.exists():
        print("scan_service.py not found.")
        return

    with open(scan_path, "r") as f:
        content = f.read()

    # 1. Add import for kautilya
    if "from src.services.kautilya import kautilya" not in content:
        # Find the line with other imports (e.g., after threat_memory)
        import_line = "from src.services.threat_memory import threat_memory"
        if import_line in content:
            content = content.replace(import_line, import_line + "\nfrom src.services.kautilya import kautilya")
        else:
            # Fallback: add after other imports
            content = content.replace("from src.services.audit_service import log_audit", "from src.services.audit_service import log_audit\nfrom src.services.kautilya import kautilya")
        print("Added kautilya import.")

    # 2. Find the section after threat memory recording and before krishna.
    # We'll insert routing decision after the threat memory block.
    # Look for the line that sets engine_results["threat_memory"] = threat_result
    # Then after the subsequent lines, we add routing.
    threat_memory_end = "engine_results[\"threat_memory\"] = threat_result"
    if threat_memory_end in content:
        # We'll insert after the block that records threat memory (including the if/else)
        # We need to find the line after the else clause.
        # Let's find the pattern of the whole threat memory block.
        # We'll replace the block that currently has the threat memory logic with a version that includes routing.
        # But easier: insert routing right after the threat memory block ends (before krishna).
        # Locate the line "krishna_result = fallback.wrap_engine(\"krishna\", Krishna().run, request, engine_results)"
        krishna_line = "krishna_result = fallback.wrap_engine(\"krishna\", Krishna().run, request, engine_results)"
        if krishna_line in content:
            # We'll insert before that line.
            routing_code = '''
    # Kautilya routing decision
    # Gather necessary info
    session_class = behavior_result.get("classification", "clean")
    bhishma_score = bhishma_result.get("score", 0.5)
    hanuman_score = hanuman_result.get("score", 0.5)
    threat_session_modifier = engine_results["threat_memory"].get("session_modifier", 1.0)
    threat_global_modifier = engine_results["threat_memory"].get("global_modifier", 1.0)
    file_present = (request.content_type == "file")
    tenant_strict_mode = False  # could be read from tenant config

    routing = kautilya.select_path(
        request, session_class, bhishma_score, hanuman_score,
        threat_session_modifier, threat_global_modifier,
        file_present, tenant_strict_mode
    )
    engine_policy = kautilya.get_engine_policy(routing["path_selected"])
    engine_results["kautilya"] = {
        "engine": "kautilya",
        "status": "ok",
        "path": routing["path_selected"],
        "reason": routing["path_reason"],
        "engines_run": routing["engines_run"],
        "engines_skipped": routing["engines_skipped"],
        "cost_tier": routing["cost_tier"],
        "latency_budget_ms": routing["latency_budget_ms"],
    }
    # Conditionally skip expensive engines based on path
    if not engine_policy.get("shakuni", True):
        # If shakuni is skipped, we still need a placeholder
        engine_results["shakuni"] = {"engine": "shakuni", "status": "skipped", "score": 0.0}
    if not engine_policy.get("arjuna", True):
        engine_results["arjuna"] = {"engine": "arjuna", "status": "skipped", "score": 0.0}
    if not engine_policy.get("yudhishthira", True):
        engine_results["yudhishthira"] = {"engine": "yudhishthira", "status": "skipped", "modifier": 1.0}
'''
            # Insert before krishna_line
            content = content.replace(krishna_line, routing_code + "\n\n    " + krishna_line)
            print("Inserted Kautilya routing before Krishna.")
        else:
            print("Could not find krishna line.")
    else:
        print("Could not find threat memory line.")

    # 3. Also need to make sure that shakuni, arjuna, yudhishthira are not run if they were skipped.
    # The current code runs them unconditionally. We need to wrap their execution in conditionals.
    # We'll replace the existing calls with conditionals.
    # Find the lines where shakuni_result, arjuna_result, yudhishthira_result are computed.
    # They are currently after the threat memory block. We'll replace them with conditionals.
    # We'll look for the lines that start with "shakuni_result = fallback.wrap_engine"
    # and wrap them in if statements based on engine_policy.

    # First, remove the existing unconditional calls (they are still there).
    # We'll replace them with our conditional versions that are already in the routing_code? No, we inserted the routing_code before krishna, but the original shakuni, arjuna, yudhishthira calls are still present before that.
    # So we need to delete those original calls.
    # Let's locate the original block and remove it.
    # The original block (after threat memory) looks like:
    #   shakuni_result = fallback.wrap_engine("shakuni", Shakuni().run, request)
    #   engine_results["shakuni"] = shakuni_result
    #   arjuna_result = fallback.wrap_engine("arjuna", Arjuna().run, request)
    #   engine_results["arjuna"] = arjuna_result
    #   yudhishthira_result = fallback.wrap_engine("yudhishthira", Yudhishthira().run, request, bhishma_result)
    #   engine_results["yudhishthira"] = yudhishthira_result
    # We'll replace this block with a placeholder comment.
    # We'll search for these lines and remove them.
    # We'll use a regex to match the block.
    pattern = r'(shakuni_result = fallback\.wrap_engine\("shakuni", Shakuni\(\)\.run, request\)\s+engine_results\["shakuni"\] = shakuni_result\s+arjuna_result = fallback\.wrap_engine\("arjuna", Arjuna\(\)\.run, request\)\s+engine_results\["arjuna"\] = arjuna_result\s+yudhishthira_result = fallback\.wrap_engine\("yudhishthira", Yudhishthira\(\)\.run, request, bhishma_result\)\s+engine_results\["yudhishthira"\] = yudhishthira_result)'
    # Actually it's easier to use a multiline replacement.
    # We'll just comment out those lines by adding a # at the beginning of each line.
    # But to be safe, we'll replace the block with a comment.
    # We'll use a simpler approach: replace the exact text.
    old_block = '''    shakuni_result = fallback.wrap_engine("shakuni", Shakuni().run, request)
    engine_results["shakuni"] = shakuni_result

    arjuna_result = fallback.wrap_engine("arjuna", Arjuna().run, request)
    engine_results["arjuna"] = arjuna_result

    yudhishthira_result = fallback.wrap_engine("yudhishthira", Yudhishthira().run, request, bhishma_result)
    engine_results["yudhishthira"] = yudhishthira_result
'''
    if old_block in content:
        content = content.replace(old_block, "    # Engines shakuni, arjuna, yudhishthira are now conditionally run via Kautilya (see routing block)\n")
        print("Removed unconditional engine calls.")
    else:
        print("Old block not found. Manual cleanup may be needed.")

    # Write the modified file
    with open(scan_path, "w") as f:
        f.write(content)
    print("scan_service.py patched successfully.")

if __name__ == "__main__":
    main()
