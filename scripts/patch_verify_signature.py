#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
from pathlib import Path

FALLBACK_FILE = Path("src/core/fallback.py")
BACKUP = FALLBACK_FILE.with_suffix(".py.sig_backup")

def patch():
    if not FALLBACK_FILE.exists():
        print("ERROR: fallback.py not found")
        return

    if not BACKUP.exists():
        BACKUP.write_text(FALLBACK_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Backup saved to {BACKUP}")

    content = FALLBACK_FILE.read_text(encoding="utf-8")

    # Add imports for hmac and os if not present
    imports_needed = ["import hmac", "import os"]
    for imp in imports_needed:
        if imp not in content:
            content = content.replace("import hashlib", "import hashlib\n" + imp)

    # Replace verify_critical_artifacts function with signature‑aware version
    new_func = '''def verify_critical_artifacts(manifest_path: Path = Path("configs/trusted_artifacts.json")) -> tuple[bool, list[str]]:
    if not manifest_path.exists():
        return False, ["trusted_artifacts.json missing"]
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except Exception as e:
        return False, [f"manifest parse error: {e}"]
    
    # Verify signature if present
    signature = manifest.get("signature")
    artifacts = manifest.get("artifacts", {})
    if signature:
        combined = "".join(f"{k}:{v.get('sha256','')}" for k, v in sorted(artifacts.items()))
        secret = os.environ.get("GARUDA_SIGNING_SECRET", "change-me-in-production")
        expected = hmac.new(secret.encode(), combined.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False, ["Manifest signature invalid"]
    
    failures = []
    for rel_path, expected in artifacts.items():
        full = Path(rel_path)
        if not full.exists():
            failures.append(f"{rel_path} missing")
            continue
        actual = compute_sha256(full)
        if actual != expected.get("sha256"):
            failures.append(f"{rel_path} checksum mismatch")
    return len(failures) == 0, failures
'''
    # Find old function and replace
    pattern = r'def verify_critical_artifacts\([^)]*\)[^:]*:.*?(?=\n\S|\Z)'
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, new_func, content, flags=re.DOTALL)
        print("verify_critical_artifacts updated with signature validation.")
    else:
        print("Could not find original function, please add manually.")

    FALLBACK_FILE.write_text(content, encoding="utf-8")
    print(f"Updated {FALLBACK_FILE}")

if __name__ == "__main__":
    patch()
