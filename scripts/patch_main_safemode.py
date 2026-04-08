#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

MAIN_FILE = Path("src/api/main.py")
if not MAIN_FILE.exists():
    MAIN_FILE = Path("src/main.py")
BACKUP = MAIN_FILE.with_suffix(".py.safemode_backup")

def patch():
    if not MAIN_FILE.exists():
        print("ERROR: main.py not found")
        return

    if not BACKUP.exists():
        BACKUP.write_text(MAIN_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Backup saved to {BACKUP}")

    content = MAIN_FILE.read_text(encoding="utf-8")

    # Look for the startup_integrity_check function
    pattern = r'(if not fallback\.check_integrity_on_startup\(\):.*?logger\.critical\([^\)]+\))'
    replacement = r'\1\n        fallback.enable_safe_mode("Integrity check failed")'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        print("Added enable_safe_mode call in startup integrity check.")
    else:
        print("Could not find integrity check block. Please manually add: fallback.enable_safe_mode('Integrity check failed')")

    MAIN_FILE.write_text(content, encoding="utf-8")
    print(f"Updated {MAIN_FILE}")

if __name__ == "__main__":
    patch()
