#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

AUDIT_SERVICE = Path("src/services/audit_service.py")
BACKUP = AUDIT_SERVICE.with_suffix(".py.loghash_backup2")

def patch():
    if not AUDIT_SERVICE.exists():
        print(f"ERROR: {AUDIT_SERVICE} not found")
        return

    # Backup
    if not BACKUP.exists():
        BACKUP.write_text(AUDIT_SERVICE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Backup saved to {BACKUP}")

    content = AUDIT_SERVICE.read_text(encoding="utf-8")

    # 1. Ensure import exists
    import_line = "from src.protection.log_integrity import compute_prev_hash"
    if import_line not in content:
        # Insert after last import
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

    # 2. Add prev_hash to audit_data dict
    # Look for pattern: audit_data = { ... } (possibly spanning multiple lines)
    # We'll insert a new key after the opening brace
    pattern = r'(audit_data\s*=\s*\{)'
    if re.search(pattern, content):
        # Insert after the opening brace, before any other keys
        replacement = r'\1\n        "prev_hash": compute_prev_hash(),'
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            content = new_content
            print("Added prev_hash field to audit_data.")
        else:
            print("No change made – prev_hash may already exist.")
    else:
        # Fallback: search for a line that starts with "audit_data =" and manually inject
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith("audit_data ="):
                # Insert a new line after it
                indent = re.match(r'(\s*)', line).group(1)
                lines.insert(i+1, f'{indent}    "prev_hash": compute_prev_hash(),')
                content = "\n".join(lines)
                print("Added prev_hash line after audit_data assignment.")
                break
        else:
            print("Could not find audit_data assignment. Please manually add:")
            print('    "prev_hash": compute_prev_hash(),')
            print("inside the audit_data dictionary, near the top.")

    AUDIT_SERVICE.write_text(content, encoding="utf-8")
    print(f"Updated {AUDIT_SERVICE}")

if __name__ == "__main__":
    patch()
