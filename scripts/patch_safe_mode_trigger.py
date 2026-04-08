#!/usr/bin/env python3
import re
from pathlib import Path

MAIN_FILE = Path("src/api/main.py")
if not MAIN_FILE.exists():
    MAIN_FILE = Path("src/main.py")

def patch():
    content = MAIN_FILE.read_text(encoding="utf-8")
    if "fallback.enable_safe_mode" in content:
        print("Safe mode activation already present.")
    else:
        # Add after integrity check failure
        new_content = re.sub(
            r'(if not fallback\.check_integrity_on_startup\(\):.*?logger\.critical\([^\)]+\))',
            r'\1\n        fallback.enable_safe_mode("Integrity check failed")',
            content, flags=re.DOTALL
        )
        MAIN_FILE.write_text(new_content, encoding="utf-8")
        print("Added safe mode activation on integrity failure.")
if __name__ == "__main__":
    patch()
