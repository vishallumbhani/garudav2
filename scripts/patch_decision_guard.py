#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

SCAN_SERVICE = Path("src/services/scan_service.py")
BACKUP = SCAN_SERVICE.with_suffix(".py.decision_guard_backup")

def patch():
    if not SCAN_SERVICE.exists():
        print(f"ERROR: {SCAN_SERVICE} not found")
        return

    # Backup
    if not BACKUP.exists():
        BACKUP.write_text(SCAN_SERVICE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Backup saved to {BACKUP}")

    content = SCAN_SERVICE.read_text(encoding="utf-8")

    # 1. Add import if missing
    import_line = "from src.resilience.decision_guard import decision_guard"
    if import_line not in content:
        # Find a place to insert (after existing resilience imports)
        lines = content.splitlines()
        insert_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("from src.playbooks") or line.startswith("from src.core.fallback"):
                insert_idx = i + 1
                break
        if insert_idx == -1:
            # fallback: insert after last import
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    insert_idx = i + 1
        if insert_idx > 0:
            lines.insert(insert_idx, import_line)
            content = "\n".join(lines)
            print("Added import for decision_guard")
        else:
            print("WARNING: Could not add import, please add manually:", import_line)

    # 2. Insert decision guard code after the line: response = sanjaya.run(...)
    pattern = r'(response\s*=\s*sanjaya\.run\(request,\s*krishna_result\))'
    replacement = r'\1\n\n    # Decision guard (Phase 5)\n    original_decision = response.decision\n    guarded_decision = decision_guard.evaluate(original_decision, response.score)\n    if guarded_decision != original_decision:\n        logger.warning(f"Decision overridden: {original_decision} -> {guarded_decision} due to degraded trust")\n        response.decision = guarded_decision'
    
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        print("Decision guard code inserted.")
    else:
        print("WARNING: Could not find 'response = sanjaya.run(...)' line. Please insert manually.")

    # Write back
    SCAN_SERVICE.write_text(content, encoding="utf-8")
    print(f"Updated {SCAN_SERVICE}")

if __name__ == "__main__":
    patch()
