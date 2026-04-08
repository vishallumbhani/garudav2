#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path

AUDIT_SERVICE = Path("src/services/audit_service.py")
BACKUP = AUDIT_SERVICE.with_suffix(".py.loghash_backup")
LOG_INTEGRITY = Path("src/protection/log_integrity.py")

def create_log_integrity_module():
    LOG_INTEGRITY.parent.mkdir(parents=True, exist_ok=True)
    code = '''import hashlib
import json
from pathlib import Path
from typing import Optional

def compute_prev_hash(audit_log_path: Path = Path("logs/audit.jsonl")) -> Optional[str]:
    """Return SHA256 of the last line in the audit log, or None if empty."""
    if not audit_log_path.exists():
        return None
    with open(audit_log_path, "rb") as f:
        last_line = None
        for line in f:
            if line.strip():
                last_line = line
    if last_line:
        return hashlib.sha256(last_line).hexdigest()
    return None
'''
    LOG_INTEGRITY.write_text(code)
    print(f"Created {LOG_INTEGRITY}")

def patch_audit_service():
    if not AUDIT_SERVICE.exists():
        print("audit_service.py not found, skipping patch.")
        return
    if not BACKUP.exists():
        BACKUP.write_text(AUDIT_SERVICE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Backup saved to {BACKUP}")

    content = AUDIT_SERVICE.read_text(encoding="utf-8")
    # Add import and prev_hash logic in log_audit function
    import_line = "from src.protection.log_integrity import compute_prev_hash"
    if import_line not in content:
        content = import_line + "\n" + content

    # Find the line where audit entry is created (e.g., audit_data dict) and add prev_hash
    # This is heuristic – look for "audit_data = {" and insert prev_hash
    if "audit_data" in content and "prev_hash" not in content:
        content = content.replace(
            'audit_data = {',
            'audit_data = {\n        "prev_hash": compute_prev_hash(),'
        )
        print("Added prev_hash field to audit_data.")
    else:
        print("Could not find audit_data dict. Please manually add 'prev_hash' field.")

    AUDIT_SERVICE.write_text(content, encoding="utf-8")
    print(f"Updated {AUDIT_SERVICE}")

if __name__ == "__main__":
    create_log_integrity_module()
    patch_audit_service()
