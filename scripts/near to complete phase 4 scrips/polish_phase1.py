#!/usr/bin/env python3
"""
Final polish:
- Add missing asyncio import in test
- Fix datetime.utcnow() deprecation
- Ensure test_api.sh works
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

def write_file(path, content):
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"Written: {file_path}")

# 1. Fix test_api.py - add asyncio import
with open("src/tests/test_api.py", "r") as f:
    content = f.read()

if "import asyncio" not in content:
    content = content.replace("import json", "import json\nimport asyncio")
    with open("src/tests/test_api.py", "w") as f:
        f.write(content)
    print("✅ Added asyncio import to test_api.py")

# 2. Fix audit_service.py datetime deprecation
with open("src/services/audit_service.py", "r") as f:
    content = f.read()

if "datetime.utcnow()" in content:
    content = content.replace("from datetime import datetime", "from datetime import datetime, timezone")
    content = content.replace("datetime.utcnow()", "datetime.now(timezone.utc)")
    with open("src/services/audit_service.py", "w") as f:
        f.write(content)
    print("✅ Fixed datetime.utcnow() in audit_service.py")

# 3. Fix any other files with datetime.utcnow()
for file_path in [
    "src/api/routes/scan_text.py",
    "src/api/routes/scan_file.py",
    "src/engines/sanjaya/engine.py",
    "src/db/init_db.py"
]:
    try:
        with open(file_path, "r") as f:
            content = f.read()
        if "datetime.utcnow()" in content:
            content = content.replace("from datetime import datetime", "from datetime import datetime, timezone")
            content = content.replace("datetime.utcnow()", "datetime.now(timezone.utc)")
            with open(file_path, "w") as f:
                f.write(content)
            print(f"✅ Fixed datetime.utcnow() in {file_path}")
    except FileNotFoundError:
        pass

# 4. Ensure jq is installed (for test_api.sh)
import subprocess
try:
    subprocess.run(["jq", "--version"], capture_output=True, check=True)
    print("✅ jq is installed")
except (subprocess.CalledProcessError, FileNotFoundError):
    print("⚠️ jq not found. Install with: sudo apt install jq")
    print("   Then run ./scripts/test_api.sh again")

# 5. Run a quick test to verify the API is working
print("\n✅ All fixes applied. Now run:")
print("   ./scripts/run_dev.sh  (in one terminal)")
print("   ./scripts/test_api.sh (in another)")
