#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

SCAN_SERVICE = Path("src/services/scan_service.py")
BACKUP = SCAN_SERVICE.with_suffix(".py.playbooks_backup")

def patch():
    if not SCAN_SERVICE.exists():
        print(f"ERROR: {SCAN_SERVICE} not found")
        return

    if not BACKUP.exists():
        BACKUP.write_text(SCAN_SERVICE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Backup saved to {BACKUP}")

    content = SCAN_SERVICE.read_text(encoding="utf-8")

    # 1. Add imports if missing
    imports_block = """
# Phase 5 playbooks
from src.playbooks.throttle import is_throttled
from src.playbooks.isolation import is_session_isolated, isolate_session
from src.playbooks.alerting import send_alert
from src.playbooks.severity import map_decision_to_severity, Severity
from src.playbooks.quarantine import quarantine_file
from src.core.fallback import fallback
"""
    if "from src.playbooks.throttle" not in content:
        lines = content.splitlines()
        last_import = -1
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                last_import = i
        if last_import >= 0:
            lines.insert(last_import + 1, imports_block)
        else:
            lines.insert(0, imports_block)
        content = "\n".join(lines)

    # 2. Add helper function if missing
    helper_func = """
def _apply_playbooks(session_id: str, decision: str, score: float, file_path: str = None):
    \"\"\"Apply throttle, isolation, alerting, quarantine based on scan result.\"\"\"
    has_failures = len(fallback.degraded_engines) > 0
    severity = map_decision_to_severity(decision, has_failures, is_session_isolated(session_id))
    
    if severity <= Severity.HIGH:
        send_alert(
            severity=int(severity),
            title=f"Scan decision: {decision}",
            description=f"Session {session_id} triggered {decision}",
            context={"score": score, "decision": decision, "engines_degraded": list(fallback.degraded_engines)}
        )
    
    if file_path and decision in ("block", "challenge"):
        from pathlib import Path
        quarantine_file(Path(file_path), reason=f"Scan decision: {decision}")
"""
    if "_apply_playbooks" not in content:
        lines = content.splitlines()
        # Find first function definition
        func_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("def ") or line.strip().startswith("async def "):
                func_idx = i
                break
        if func_idx >= 0:
            lines.insert(func_idx, helper_func)
            content = "\n".join(lines)

    # 3. Patch return statements - more flexible regex
    # Look for return statement that returns a ScanResponse (maybe without parentheses)
    # Pattern: return ScanResponse( ... ) or return ScanResponse( ... ) with newlines
    pattern = r'(return\s+ScanResponse\s*\()'
    if re.search(pattern, content, re.DOTALL):
        # Insert the playbooks call right before the return
        # We'll capture the indentation of the return line
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            if re.search(r'^\s*return\s+ScanResponse\s*\(', line):
                # Determine indentation
                indent = re.match(r'(\s*)', line).group(1)
                # Insert the call with same indentation
                new_lines.append(f"{indent}_apply_playbooks(session_id, decision, final_score, getattr(request, 'file_path', None))")
                new_lines.append(line)
            else:
                new_lines.append(line)
        content = "\n".join(new_lines)
        print("Patched scan_text to call _apply_playbooks before return.")
    else:
        # Alternative: search for just "return" with ScanResponse in same line
        pattern2 = r'return\s+ScanResponse\([^)]*\)'
        if re.search(pattern2, content):
            content = re.sub(pattern2, r'_apply_playbooks(session_id, decision, final_score, getattr(request, "file_path", None))\n    \g<0>', content)
            print("Patched using alternative pattern.")
        else:
            print("WARNING: Could not find return statement. Please manually add the call.")
            print("Add this line before any 'return ScanResponse(...)':")
            print('_apply_playbooks(session_id, decision, final_score, getattr(request, "file_path", None))')

    SCAN_SERVICE.write_text(content, encoding="utf-8")
    print(f"Updated {SCAN_SERVICE}")

if __name__ == "__main__":
    patch()
