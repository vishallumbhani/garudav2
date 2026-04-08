#!/usr/bin/env python3

import importlib
import os
import sys
from pathlib import Path

print("=" * 100)
print("GARUDA PHASE 1–4 VALIDATION")
print("=" * 100)

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def check_import(module):
    try:
        importlib.import_module(module)
        print(f"[PASS] {module}")
    except Exception as e:
        print(f"[FAIL] {module} -> {e}")


def check_file(path):
    if path.exists():
        print(f"[PASS] {path}")
    else:
        print(f"[FAIL] {path}")


# =========================
# Phase 1 — Core + API
# =========================
print("\n--- Phase 1: Core / API ---")

phase1_modules = [
    "core.config",
    "core.models",
    "core.fallback",
    "db.base",
    "db.models",
    "auth.jwt_service",
    "auth.api_key_service",
    "api.main",
    "api.routes.scan_text",
    "api.routes.scan_file",
    "api.routes.audit",
]

for m in phase1_modules:
    check_import(m)


# =========================
# Phase 2 — Engines
# =========================
print("\n--- Phase 2: Engines ---")

engines = [
    "engines.arjuna.engine",
    "engines.bhishma.engine",
    "engines.shakuni.engine",
    "engines.hanuman.engine",
    "engines.krishna.engine",
    "engines.sanjaya.engine",
    "engines.yudhishthira.engine",
]

for e in engines:
    check_import(e)


# =========================
# Phase 3 — Services
# =========================
print("\n--- Phase 3: Services ---")

services = [
    "services.scan_service",
    "services.audit_service",
    "services.behavior_service",
    "services.threat_memory",
    "services.rag_protection",
]

for s in services:
    check_import(s)


# =========================
# Phase 4 — Advanced
# =========================
print("\n--- Phase 4: Advanced ---")

advanced_checks = [
    BASE_DIR / "data/uploads",
    BASE_DIR / "data/processed",
    BASE_DIR / "logs/audit.jsonl",
]

for p in advanced_checks:
    check_file(p)


# =========================
# Model + Rules check
# =========================
print("\n--- Model & Rules ---")

critical_files = [
    BASE_DIR / "models/arjuna_model.pkl",
    BASE_DIR / "models/arjuna_vectorizer.pkl",
    BASE_DIR / "models/arjuna_label_map.json",
    BASE_DIR / "src/engines/bhishma/rules.yaml",
    BASE_DIR / "src/engines/shakuni/rules.yaml",
]

for f in critical_files:
    check_file(f)


print("\nValidation Complete.")
