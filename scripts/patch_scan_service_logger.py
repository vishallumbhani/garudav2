#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

SCAN_SERVICE = Path("src/services/scan_service.py")
BACKUP = SCAN_SERVICE.with_suffix(".py.logger_backup")

def patch():
    if not SCAN_SERVICE.exists():
        print("ERROR: scan_service.py not found")
        return

    # Backup
    if not BACKUP.exists():
        BACKUP.write_text(SCAN_SERVICE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Backup saved to {BACKUP}")

    content = SCAN_SERVICE.read_text(encoding="utf-8")

    # Add import logging if missing
    if "import logging" not in content:
        # Insert at top after other imports
        lines = content.splitlines()
        # Find the first non-import line
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                insert_idx = i + 1
            else:
                break
        lines.insert(insert_idx, "import logging")
        content = "\n".join(lines)
        print("Added import logging.")

    # Add logger definition after imports
    logger_line = "logger = logging.getLogger(__name__)"
    if logger_line not in content:
        # Find a good place: after all imports but before first function
        lines = content.splitlines()
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                insert_idx = i + 1
            elif line.strip() and not line.startswith("#"):
                break
        lines.insert(insert_idx, logger_line)
        content = "\n".join(lines)
        print("Added logger definition.")

    SCAN_SERVICE.write_text(content, encoding="utf-8")
    print(f"Updated {SCAN_SERVICE}")

if __name__ == "__main__":
    patch()
