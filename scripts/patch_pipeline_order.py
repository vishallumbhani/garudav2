#!/usr/bin/env python3
import re
from pathlib import Path

SCAN_SERVICE = Path("src/services/scan_service.py")
BACKUP = SCAN_SERVICE.with_suffix(".py.pipeline_backup")

def patch():
    if not SCAN_SERVICE.exists():
        print("ERROR: scan_service.py not found")
        return

    if not BACKUP.exists():
        BACKUP.write_text(SCAN_SERVICE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Backup saved to {BACKUP}")

    content = SCAN_SERVICE.read_text(encoding="utf-8")

    # Insert pipeline section comments before major blocks
    markers = [
        ("# 1. NORMALIZATION (already done before _run_pipeline)", "request.normalized_text"),
        ("# 2. INTEGRITY PRECHECK (startup only, skip runtime)", "engine_results = {}"),
        ("# 3. ENGINE EXECUTION (with health tracking)", "hanuman_result = fallback.wrap_engine"),
        ("# 4. RESILIENCE STATE (degraded engines, circuit breakers)", "behavior_result ="),
        ("# 5. BASE DECISION (Sanjaya)", "response = sanjaya.run"),
        ("# 6. DECISION GUARD", "decision_guard.evaluate"),
        ("# 7. PLAYBOOKS", "_apply_playbooks"),
        ("# 8. AUDIT & PERSIST", "async with AsyncSessionLocal"),
    ]

    for comment, pattern in markers:
        if comment not in content:
            # Find line containing pattern and insert comment above it
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if pattern in line:
                    lines.insert(i, comment)
                    break
            content = "\n".join(lines)

    SCAN_SERVICE.write_text(content, encoding="utf-8")
    print("Pipeline order comments added.")

if __name__ == "__main__":
    patch()
