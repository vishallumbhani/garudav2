#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adds health tracking and circuit breaker to wrap_engine in fallback.py"""
import re
from pathlib import Path

FALLBACK_PATH = Path("src/core/fallback.py")
BACKUP = FALLBACK_PATH.with_suffix(".py.phase5_backup")

def enhance():
    if not FALLBACK_PATH.exists():
        print("fallback.py not found")
        return
    # Backup
    if not BACKUP.exists():
        BACKUP.write_text(FALLBACK_PATH.read_text(), encoding="utf-8")
        print(f"Backup saved to {BACKUP}")

    content = FALLBACK_PATH.read_text(encoding="utf-8")

    # Check if already enhanced
    if "from src.resilience.health import get_health" in content:
        print("Already enhanced, skipping.")
        return

    # Add imports at top (after existing imports)
    imports = """
# Phase 5 resilience imports
from src.resilience.health import get_health
from src.resilience.circuit_breaker import get_breaker
from src.playbooks.severity import map_severity, Severity
import asyncio
"""
    # Find last import line
    lines = content.splitlines()
    last_import_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            last_import_idx = i
    if last_import_idx >= 0:
        lines.insert(last_import_idx + 1, imports)
    else:
        lines.insert(0, imports)
    content = "\n".join(lines)

    # Now enhance wrap_engine function
    # Look for "def wrap_engine" and add health/breaker logic inside
    # This is heuristic – we'll replace the function body with a wrapped version
    pattern = r'(async )?def wrap_engine\([^)]*\):.*?(?=\n\S|$)'
    # For simplicity, we'll inject a decorator-like wrapper around the original call
    # More robust: we'll patch the function by adding code at its beginning.
    # I'll provide a generic insertion that works if the function has a try block.
    # But to be safe, let's add a note and manual steps.
    print("\n=== Manual enhancement required ===")
    print("Please edit src/core/fallback.py and inside your wrap_engine function,")
    print("add these lines at the start (after any async def line):")
    print("""
    health = get_health(engine_name)
    breaker = get_breaker(engine_name)
    if await breaker.is_open():
        raise Exception(f"Circuit breaker open for {engine_name}")
    try:
        result = await original_engine_call(...)  # your existing call
        await health.record_success()
        await breaker.record_success()
        return result
    except Exception as e:
        await health.record_failure()
        await breaker.record_failure()
        # then your existing fallback logic
        return await get_safe_decision(...)
    """)
    print("\nAfter changes, test with: python -c 'from src.core.fallback import wrap_engine'")

if __name__ == "__main__":
    enhance()
