#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

AUDIT_FILE = Path("src/services/audit_service.py")
BACKUP = AUDIT_FILE.with_suffix(".py.prevhash_backup")

def patch():
    if not AUDIT_FILE.exists():
        print("ERROR: audit_service.py not found")
        return

    # Backup
    if not BACKUP.exists():
        BACKUP.write_text(AUDIT_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Backup saved to {BACKUP}")

    content = AUDIT_FILE.read_text(encoding="utf-8")

    # Ensure import is present
    import_line = "from src.protection.log_integrity import compute_prev_hash"
    if import_line not in content:
        # Insert after the last import
        lines = content.splitlines()
        last_import = -1
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                last_import = i
        if last_import >= 0:
            lines.insert(last_import + 1, import_line)
        else:
            lines.insert(0, import_line)
        content = "\n".join(lines)
        print("Added import for compute_prev_hash.")

    # Add prev_hash insertion before JSONL write
    # Look for the line: "with open(log_path, \"a\", encoding=\"utf-8\") as f:"
    pattern = r'(with open\(log_path, "a", encoding="utf-8"\) as f:)'
    replacement = r'    # Phase 5: add hash chain\n    event_data["prev_hash"] = compute_prev_hash()\n    \1'
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        print("Added prev_hash insertion before JSONL write.")
    else:
        print("Could not find the 'with open(log_path...' line. Please manually add:")
        print('    event_data["prev_hash"] = compute_prev_hash()')
        print("right before the 'with open(...)' line.")

    AUDIT_FILE.write_text(content, encoding="utf-8")
    print(f"Updated {AUDIT_FILE}")

if __name__ == "__main__":
    patch()
