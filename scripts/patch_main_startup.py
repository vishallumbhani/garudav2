#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

def patch():
    # Define paths inside function, not as global
    main_path = Path("src/api/main.py")
    if not main_path.exists():
        main_path = Path("src/main.py")
        if not main_path.exists():
            print("No main.py found. Please manually add startup check.")
            return
    
    backup = main_path.with_suffix(".py.startup_backup")
    if not backup.exists():
        backup.write_text(main_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Backup saved to {backup}")

    content = main_path.read_text(encoding="utf-8")

    # Add import if missing
    import_line = "from src.core.fallback import fallback"
    if import_line not in content:
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

    # Add startup event if not exists
    startup_block = """
@app.on_event("startup")
async def startup_integrity_check():
    from src.core.fallback import fallback
    import logging
    logger = logging.getLogger(__name__)
    if not fallback.check_integrity_on_startup():
        logger.critical("Integrity check failed - Garuda may be compromised")
"""
    if "startup_integrity_check" not in content:
        # Look for app = FastAPI(...) line
        pattern = r'(app\s*=\s*FastAPI\([^)]*\))'
        if re.search(pattern, content):
            content = re.sub(pattern, r'\1\n' + startup_block, content)
            print("Startup integrity check added.")
        else:
            print("WARNING: Could not find 'app = FastAPI(...)'. Please add manually:\n" + startup_block)

    main_path.write_text(content, encoding="utf-8")
    print(f"Updated {main_path}")

if __name__ == "__main__":
    patch()
