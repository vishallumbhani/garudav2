#!/usr/bin/env python3
"""
Fix datetime offset issue in audit_service.py.
Convert timezone-aware UTC to naive datetime for TIMESTAMP WITHOUT TIME ZONE column.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

with open("src/services/audit_service.py", "r") as f:
    content = f.read()

# Replace the created_at line
old_line = "created_at=datetime.now(timezone.utc),"
new_line = "created_at=datetime.now(timezone.utc).replace(tzinfo=None),"

if old_line in content:
    content = content.replace(old_line, new_line)
    with open("src/services/audit_service.py", "w") as f:
        f.write(content)
    print("✅ Fixed datetime in audit_service.py")
else:
    print("No change needed (line not found).")

# Also ensure the import includes timezone (already does)
