#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

FALLBACK_FILE = Path("src/core/fallback.py")
BACKUP = FALLBACK_FILE.with_suffix(".py.safemode_backup")

def patch():
    if not FALLBACK_FILE.exists():
        print("ERROR: fallback.py not found")
        return

    # Backup
    if not BACKUP.exists():
        BACKUP.write_text(FALLBACK_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Backup saved to {BACKUP}")

    content = FALLBACK_FILE.read_text(encoding="utf-8")

    # Check if method already exists
    if "def enable_safe_mode" in content:
        print("enable_safe_mode already present, skipping.")
        return

    # Find the class FallbackManager and add method before the last method (or at end)
    # We'll insert after the get_safe_decision method or before the final return
    method_code = """
    def enable_safe_mode(self, reason: str):
        \"\"\"Activate safe mode, typically due to integrity failure.\"\"\"
        self.safe_mode = True
        logger.critical(f"Safe mode enabled: {reason}")
"""
    # Find the class definition and locate a good insertion point (after get_safe_decision)
    if "def get_safe_decision" in content:
        # Insert after that method
        pattern = r'(def get_safe_decision\([^\)]*\)[^:]*:.*?(?=\n    def|\nclass|\Z))'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            insert_pos = match.end()
            content = content[:insert_pos] + "\n" + method_code + content[insert_pos:]
            print("enable_safe_mode added after get_safe_decision.")
        else:
            print("Could not locate get_safe_decision, adding at end of class.")
            # Add at end of class (before the line with 'fallback = FallbackManager()')
            content = content.replace("fallback = FallbackManager()", method_code + "\nfallback = FallbackManager()")
    else:
        print("Could not find get_safe_decision, adding at end of class.")
        content = content.replace("fallback = FallbackManager()", method_code + "\nfallback = FallbackManager()")

    FALLBACK_FILE.write_text(content, encoding="utf-8")
    print(f"Updated {FALLBACK_FILE}")

if __name__ == "__main__":
    patch()
