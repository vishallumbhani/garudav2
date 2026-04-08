#!/usr/bin/env python3
"""
Garuda Status Checker - Verifies Phases 1 to 4
Phase 1: Input validation & extraction
Phase 2: Multi-engine detection (Arjuna, Bhishma, Shakuni, etc.)
Phase 3: Response & threat memory (quarantine, audit, fallback)
Phase 4: Adaptive protection (behavioural analysis, RAG protection)
"""

import os
import sys
import json
import subprocess
import sqlite3  # or psycopg2 if you use PostgreSQL
from pathlib import Path
from datetime import datetime, timedelta

# ---------- Configuration ----------
BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
DB_PATH = BASE_DIR / "garuda_db_backup.sql"  # adjust if using PostgreSQL
CONFIG_FILE = BASE_DIR / "src" / "core" / "config.py"
MODELS_DIR = BASE_DIR / "models"
ENGINES_DIR = BASE_DIR / "src" / "engines"
UPLOADS_DIR = BASE_DIR / "data" / "uploads"
QUARANTINE_DIR = BASE_DIR / "data" / "quarantine"
AUDIT_LOG = LOGS_DIR / "audit.jsonl"
APP_LOG = LOGS_DIR / "app.log"

# Health endpoint (adjust if your API runs on different port)
API_URL = "http://localhost:8000/health"

# ---------- Helper Functions ----------
def print_section(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")

def check_file(path, description):
    exists = path.exists() and path.is_file()
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {path}")
    return exists

def check_dir(path, description):
    exists = path.exists() and path.is_dir()
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {path}")
    return exists

def check_config_value(key, expected_substring=None):
    """Simple check for config variables (heuristic)."""
    try:
        with open(CONFIG_FILE, "r") as f:
            content = f.read()
        if key in content:
            if expected_substring:
                if expected_substring in content:
                    print(f"✅ Config '{key}' contains '{expected_substring}'")
                    return True
                else:
                    print(f"⚠️ Config '{key}' found but missing '{expected_substring}'")
                    return False
            else:
                print(f"✅ Config '{key}' present")
                return True
        else:
            print(f"❌ Config '{key}' not found")
            return False
    except Exception as e:
        print(f"❌ Cannot read {CONFIG_FILE}: {e}")
        return False

def check_db_connection():
    """Attempt to connect to SQLite (or fallback to PostgreSQL)."""
    try:
        # Try SQLite first (common for dev)
        conn = sqlite3.connect(str(BASE_DIR / "garuda.db"))
        conn.execute("SELECT 1")
        conn.close()
        print("✅ Database (SQLite) reachable")
        return True
    except:
        try:
            # If you use PostgreSQL, adjust DSN
            import psycopg2
            conn = psycopg2.connect(
                dbname="garuda", user="postgres", password="", host="localhost"
            )
            conn.close()
            print("✅ Database (PostgreSQL) reachable")
            return True
        except:
            print("⚠️ Database not reachable (SQLite or PostgreSQL) – check configuration")
            return False

def check_engine_loading(engine_name):
    engine_path = ENGINES_DIR / engine_name / "engine.py"
    if not engine_path.exists():
        print(f"❌ Engine '{engine_name}' missing engine.py")
        return False
    try:
        # Dynamically import the engine module
        import importlib.util
        spec = importlib.util.spec_from_file_location(f"engine_{engine_name}", engine_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "analyze") or hasattr(module, "scan"):
            print(f"✅ Engine '{engine_name}' loads and has scan method")
            return True
        else:
            print(f"⚠️ Engine '{engine_name}' loads but no 'analyze'/'scan' method")
            return False
    except Exception as e:
        print(f"❌ Engine '{engine_name}' failed to load: {e}")
        return False

def check_api_health():
    try:
        import requests
        resp = requests.get(API_URL, timeout=3)
        if resp.status_code == 200:
            print(f"✅ API health endpoint responds (status {resp.status_code})")
            return True
        else:
            print(f"⚠️ API health returned status {resp.status_code}")
            return False
    except ImportError:
        print("⚠️ 'requests' not installed – skipping API health check")
        return False
    except Exception as e:
        print(f"❌ API health check failed: {e}")
        return False

def check_log_integrity():
    if not AUDIT_LOG.exists():
        print("❌ Audit log missing")
        return False
    try:
        # Check last 10 lines for JSON format
        with open(AUDIT_LOG, "r") as f:
            lines = f.readlines()[-10:]
        for i, line in enumerate(lines):
            if line.strip():
                json.loads(line)
        print(f"✅ Audit log exists and last 10 lines are valid JSON")
        return True
    except Exception as e:
        print(f"❌ Audit log corrupt: {e}")
        return False

def check_quarantine_function():
    if not QUARANTINE_DIR.exists():
        print("❌ Quarantine directory missing")
        return False
    # Check if there's any quarantine metadata in DB or files
    try:
        # Look for any file inside quarantine
        items = list(QUARANTINE_DIR.glob("*"))
        if items:
            print(f"✅ Quarantine directory has {len(items)} items")
        else:
            print("ℹ️ Quarantine directory is empty (no incidents yet)")
        return True
    except Exception as e:
        print(f"⚠️ Could not read quarantine dir: {e}")
        return False

def run_end_to_end_scan():
    """Simple test: upload a benign file and verify response."""
    test_file = BASE_DIR / "benign.pdf"
    if not test_file.exists():
        print("⚠️ Skipping E2E scan test: benign.pdf not found")
        return False
    try:
        import requests
        with open(test_file, "rb") as f:
            files = {"file": f}
            resp = requests.post("http://localhost:8000/scan/file", files=files, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "threat_score" in data:
                print(f"✅ E2E scan works – threat_score={data.get('threat_score')}")
                return True
            else:
                print(f"⚠️ E2E scan returned 200 but missing 'threat_score': {data}")
                return False
        else:
            print(f"❌ E2E scan failed with status {resp.status_code}: {resp.text[:200]}")
            return False
    except ImportError:
        print("⚠️ 'requests' not installed – skipping E2E scan test")
        return False
    except Exception as e:
        print(f"❌ E2E scan error: {e}")
        return False

# ---------- Phase Checks ----------
def phase1_input_validation():
    print_section("Phase 1: Input Validation & Extraction")
    ok = True
    ok &= check_dir(UPLOADS_DIR, "Uploads directory")
    ok &= check_file(BASE_DIR / "src" / "utils" / "file_extractors.py", "File extractor module")
    ok &= check_file(BASE_DIR / "src" / "utils" / "ocr.py", "OCR module")
    ok &= check_config_value("MAX_FILE_SIZE", "MAX_FILE_SIZE")
    ok &= check_config_value("ALLOWED_EXTENSIONS", ".pdf")
    # Check if a sample upload works (optional)
    return ok

def phase2_multi_engine():
    print_section("Phase 2: Multi-Engine Detection")
    engines = ["arjuna", "bhishma", "shakuni", "krishna", "hanuman", "yudhishthira"]
    ok = True
    for eng in engines:
        if check_dir(ENGINES_DIR / eng, f"Engine {eng.capitalize()} directory"):
            ok &= check_engine_loading(eng)
        else:
            ok = False
    ok &= check_file(MODELS_DIR / "arjuna_model.pkl", "Arjuna ML model")
    ok &= check_file(MODELS_DIR / "arjuna_vectorizer.pkl", "Arjuna vectorizer")
    ok &= check_file(ENGINES_DIR / "bhishma" / "rules.yaml", "Bhishma rules")
    ok &= check_file(ENGINES_DIR / "shakuni" / "rules.yaml", "Shakuni rules")
    return ok

def phase3_response_memory():
    print_section("Phase 3: Response & Threat Memory")
    ok = True
    ok &= check_dir(QUARANTINE_DIR, "Quarantine directory")
    ok &= check_file(AUDIT_LOG, "Audit log (JSONL)")
    ok &= check_file(BASE_DIR / "src" / "services" / "threat_memory.py", "Threat memory service")
    ok &= check_file(BASE_DIR / "src" / "core" / "fallback.py", "Fallback handler")
    ok &= check_db_connection()
    ok &= check_log_integrity()
    ok &= check_quarantine_function()
    return ok

def phase4_adaptive_protection():
    print_section("Phase 4: Adaptive Protection")
    ok = True
    ok &= check_file(BASE_DIR / "src" / "services" / "behavior_service.py", "Behavioural analysis service")
    ok &= check_file(BASE_DIR / "src" / "services" / "rag_protection.py", "RAG protection service")
    ok &= check_file(BASE_DIR / "src" / "services" / "kautilya.py", "Kautilya (strategy) service")
    ok &= check_file(BASE_DIR / "src" / "api" / "routes" / "overrides.py", "Override routes")
    # Check if overrides can be loaded (optional)
    ok &= check_config_value("BEHAVIOR_WINDOW_MINUTES", "BEHAVIOR_WINDOW")
    ok &= check_config_value("RAG_ENABLED", "RAG_ENABLED")
    return ok

# ---------- Main ----------
def main():
    print("🔍 Garuda Status Report")
    print(f"Timestamp: {datetime.now()}")
    print(f"Base directory: {BASE_DIR}")

    results = {}
    results["Phase1"] = phase1_input_validation()
    results["Phase2"] = phase2_multi_engine()
    results["Phase3"] = phase3_response_memory()
    results["Phase4"] = phase4_adaptive_protection()

    print_section("Live Service Checks")
    api_ok = check_api_health()
    e2e_ok = run_end_to_end_scan()

    print_section("Summary")
    for phase, ok in results.items():
        print(f"{phase}: {'✅ PASS' if ok else '❌ FAIL'}")
    print(f"API Health: {'✅ UP' if api_ok else '❌ DOWN'}")
    print(f"E2E Scan:   {'✅ PASS' if e2e_ok else '❌ FAIL'}")

    overall = all(results.values()) and api_ok and e2e_ok
    print(f"\nOverall Status: {'✅ ALL SYSTEMS GO' if overall else '⚠️ SOME CHECKS FAILED'}")
    sys.exit(0 if overall else 1)

if __name__ == "__main__":
    main()
