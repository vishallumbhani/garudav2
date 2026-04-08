#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verifies critical files exist and extracts function signatures for Phase 5 integration."""
import ast
import json
from pathlib import Path

def get_function_names(filepath: Path):
    """Return set of top-level function names in a Python file."""
    if not filepath.exists():
        return set()
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    except Exception as e:
        return {"ERROR": str(e)}

def main():
    base = Path.cwd()
    results = {}

    # 1. Scan service
    scan_service = base / "src/services/scan_service.py"
    results["scan_service_exists"] = scan_service.exists()
    if scan_service.exists():
        results["scan_functions"] = list(get_function_names(scan_service))
        # Look for scan_text, scan_file, scan, etc.
        try:
            with open(scan_service, "r", encoding="utf-8") as f:
                for line in f:
                    if "def scan" in line:
                        results["scan_signature_hint"] = line.strip()
                        break
        except:
            results["scan_signature_hint"] = "could not read"

    # 2. Fallback
    fallback = base / "src/core/fallback.py"
    results["fallback_exists"] = fallback.exists()
    if fallback.exists():
        results["fallback_functions"] = list(get_function_names(fallback))

    # 3. Audit service
    audit = base / "src/services/audit_service.py"
    results["audit_exists"] = audit.exists()
    if audit.exists():
        results["audit_functions"] = list(get_function_names(audit))

    # 4. Extractors
    extractor = base / "src/utils/file_extractors_v2.py"
    results["extractor_v2_exists"] = extractor.exists()
    if extractor.exists():
        results["extractor_functions"] = list(get_function_names(extractor))

    # 5. Engines – check main engine modules
    engines_dir = base / "src/engines"
    results["engine_modules"] = [p.name for p in engines_dir.iterdir() if (p / "engine.py").exists()]

    # 6. DB init
    db_init = base / "src/db/init_db.py"
    results["db_init_exists"] = db_init.exists()

    # 7. Redis / memory service
    threat_memory = base / "src/services/threat_memory.py"
    results["threat_memory_exists"] = threat_memory.exists()

    # Print summary
    print("=== Existing File Verification ===\n")
    for key, value in results.items():
        print(f"{key}: {value}")

    # Save for later
    with open("phase5_verification.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    print("\nVerification saved to phase5_verification.json")

if __name__ == "__main__":
    main()
