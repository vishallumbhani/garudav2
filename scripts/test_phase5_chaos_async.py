#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import shutil
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from src.services.scan_service import scan_text
from src.core.fallback import get_safe_decision

async def test_engine_failure():
    model = Path("src/engines/arjuna/arjuna_model.pkl")
    if not model.exists():
        print("SKIP: model missing")
        return
    backup = model.with_suffix(".pkl.bak")
    shutil.move(model, backup)
    try:
        from src.schemas import ScanRequest  # adjust import if needed
        req = ScanRequest(text="Hello", session_id="test")
        resp = await scan_text(req)
        if hasattr(resp, "fallback_used") and resp.fallback_used:
            print("PASS: Engine failure -> fallback used")
        else:
            print("FAIL: No fallback")
    except Exception as e:
        print(f"FAIL: Exception {e}")
    finally:
        shutil.move(backup, model)

async def main():
    await test_engine_failure()
    # Add other tests similarly

if __name__ == "__main__":
    asyncio.run(main())
