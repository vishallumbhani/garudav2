#!/usr/bin/env python3
"""
Garuda Phase 3 Full Validation Script

Covers:
  3.1 File security expansion
  3.2 Code security layer
  3.3 Image and OCR layer
  3.4 Data classification
  3.5 RAG protection

What it does:
  - Calls /v1/scan/text for text/code/data-classification checks
  - Calls /v1/scan/file for doc/file/image OCR checks
  - Optionally runs local RAG test script if present
  - Prints a readable summary
  - Saves JSON and CSV results under test_results/

Usage:
  python scripts/test_phase3_full.py

Notes:
  - Assumes API is running on http://127.0.0.1:8000
  - Assumes some test files may already exist:
      benign.pdf
      suspicious.pdf
      simple.pdf
      test.csv
      test.json
      test.log
      test.docx
      test_screenshot.png
  - If some files do not exist, this script will generate a few simple ones.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import subprocess
import sys
import textwrap
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

API_BASE = "http://127.0.0.1:8000"
TEXT_URL = f"{API_BASE}/v1/scan/text"
FILE_URL = f"{API_BASE}/v1/scan/file"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_RESULTS_DIR = PROJECT_ROOT / "test_results"
TEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

TIMEOUT = 30


@dataclass
class TestResult:
    phase: str
    area: str
    name: str
    expected: str
    passed: bool
    decision: Optional[str] = None
    score: Optional[Any] = None
    notes: str = ""
    response_excerpt: str = ""


def short_json(obj: Any, limit: int = 400) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False)
    except Exception:
        s = str(obj)
    return s if len(s) <= limit else s[:limit] + "..."


def post_text(
    text: str,
    session_id: Optional[str] = None,
    tenant_id: str = "default",
    user_id: str = "tester",
    token: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {
        "text": text,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "session_id": session_id or f"phase3_{uuid.uuid4().hex[:8]}",
    }
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.post(TEXT_URL, headers=headers, json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def post_file(
    file_path: Path,
    session_id: Optional[str] = None,
    tenant_id: str = "default",
    user_id: str = "tester",
    token: Optional[str] = None,
) -> Dict[str, Any]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with file_path.open("rb") as f:
        files = {"file": (file_path.name, f)}
        data = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "session_id": session_id or f"phase3_{uuid.uuid4().hex[:8]}",
        }
        resp = requests.post(FILE_URL, headers=headers, files=files, data=data, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()


def get_trace(resp: Dict[str, Any]) -> Dict[str, Any]:
    return resp.get("details", {}).get("trace", {})


def get_decision(resp: Dict[str, Any]) -> Optional[str]:
    return resp.get("decision")


def get_score(resp: Dict[str, Any]) -> Optional[Any]:
    return resp.get("score")


def ensure_text_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def ensure_csv_file(path: Path) -> None:
    if path.exists():
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "age", "city"])
        writer.writerow(["Alice", "30", "London"])


def ensure_json_file(path: Path) -> None:
    if path.exists():
        return
    path.write_text(json.dumps({"name": "Alice", "age": 30}, indent=2), encoding="utf-8")


def ensure_log_file(path: Path) -> None:
    if path.exists():
        return
    path.write_text("2026-04-03 10:00:00 INFO service started\n", encoding="utf-8")


def maybe_make_screenshot(path: Path) -> None:
    if path.exists():
        return
    convert_bin = shutil_which("convert")
    if not convert_bin:
        return
    try:
        subprocess.run(
            [
                convert_bin,
                "-size", "500x120",
                "xc:white",
                "-fill", "black",
                "-pointsize", "20",
                "-annotate", "+10+40",
                "API_KEY=sk-1234567890",
                str(path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def shutil_which(name: str) -> Optional[str]:
    from shutil import which
    return which(name)


def maybe_create_pdf_with_reportlab(path: Path, text: str) -> bool:
    if path.exists():
        return True
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        c = canvas.Canvas(str(path), pagesize=letter)
        c.drawString(72, 720, text)
        c.save()
        return True
    except Exception:
        return False


def maybe_create_docx(path: Path, text: str) -> bool:
    if path.exists():
        return True
    try:
        from docx import Document
        doc = Document()
        doc.add_paragraph(text)
        doc.save(str(path))
        return True
    except Exception:
        return False


def expect_decision(resp: Dict[str, Any], allowed: List[str]) -> bool:
    return get_decision(resp) in allowed


def contains_all(values: List[str], required: List[str]) -> bool:
    value_set = set(values or [])
    return all(x in value_set for x in required)


def run_phase_31_files(results: List[TestResult], token: Optional[str]) -> None:
    files_dir = PROJECT_ROOT

    test_csv = files_dir / "test.csv"
    test_json = files_dir / "test.json"
    test_log = files_dir / "test.log"
    test_docx = files_dir / "test.docx"
    simple_pdf = files_dir / "simple.pdf"
    benign_pdf = files_dir / "benign.pdf"
    suspicious_pdf = files_dir / "suspicious.pdf"

    ensure_csv_file(test_csv)
    ensure_json_file(test_json)
    ensure_log_file(test_log)
    maybe_create_docx(test_docx, "This is a benign DOCX document.")
    maybe_create_pdf_with_reportlab(simple_pdf, "Hello World")
    maybe_create_pdf_with_reportlab(benign_pdf, "This is a benign PDF document.")
    maybe_create_pdf_with_reportlab(suspicious_pdf, "API_KEY=sk-1234567890")

    file_cases = [
        ("CSV benign", test_csv, "allow_or_monitor"),
        ("JSON benign", test_json, "allow_or_monitor"),
        ("LOG benign", test_log, "allow_or_monitor"),
        ("DOCX benign", test_docx, "allow_or_monitor"),
        ("PDF benign", benign_pdf, "allow_or_monitor"),
        ("PDF suspicious", suspicious_pdf, "challenge_or_block"),
    ]

    for name, path, expected in file_cases:
        if not path.exists():
            results.append(TestResult(
                phase="3.1",
                area="file_security",
                name=name,
                expected=expected,
                passed=False,
                notes=f"Missing test file: {path}",
            ))
            continue

        try:
            resp = post_file(path, token=token)
            decision = get_decision(resp)
            trace = get_trace(resp)

            if expected == "allow_or_monitor":
                passed = decision in {"allow", "monitor", "challenge"}
            else:
                passed = decision in {"challenge", "block"}

            notes = ""
            if path.suffix.lower() == ".csv":
                notes = f"content_kind={trace.get('hanuman_content_kind')}, doc_hint={trace.get('hanuman_document_type_hint')}"
            elif path.suffix.lower() == ".json":
                notes = f"content_kind={trace.get('hanuman_content_kind')}, doc_hint={trace.get('hanuman_document_type_hint')}"
            elif path.suffix.lower() == ".log":
                notes = f"content_kind={trace.get('hanuman_content_kind')}, log_hint={trace.get('hanuman_log_type_hint')}"
            elif path.suffix.lower() == ".pdf":
                notes = f"content_kind={trace.get('hanuman_content_kind')}, metadata={short_json(trace.get('file_metadata', {}), 180)}"
            elif path.suffix.lower() == ".docx":
                notes = f"content_kind={trace.get('hanuman_content_kind')}, doc_hint={trace.get('hanuman_document_type_hint')}"

            results.append(TestResult(
                phase="3.1",
                area="file_security",
                name=name,
                expected=expected,
                passed=passed,
                decision=decision,
                score=get_score(resp),
                notes=notes,
                response_excerpt=short_json(trace, 250),
            ))
        except Exception as e:
            results.append(TestResult(
                phase="3.1",
                area="file_security",
                name=name,
                expected=expected,
                passed=False,
                notes=f"Exception: {e}",
            ))


def run_phase_32_code(results: List[TestResult], token: Optional[str]) -> None:
    cases = [
        (
            "Benign Python code",
            "def add(a, b): return a + b",
            "allow",
            lambda resp: (
                get_decision(resp) == "allow"
                and not get_trace(resp).get("hanuman_detected_dangerous_functions")
            ),
        ),
        (
            "Dangerous os.system",
            'import os; os.system("ls")',
            "challenge_or_block",
            lambda resp: (
                get_decision(resp) in {"challenge", "block"}
                and "os.system" in (get_trace(resp).get("hanuman_detected_dangerous_functions") or [])
            ),
        ),
        (
            "Dangerous subprocess",
            'import subprocess; subprocess.Popen("id", shell=True)',
            "challenge_or_block",
            lambda resp: (
                get_decision(resp) in {"challenge", "block"}
                and any("subprocess" in x for x in (get_trace(resp).get("hanuman_detected_dangerous_functions") or []))
            ),
        ),
        (
            "Generic secret",
            'DB_PASSWORD="supersecret123"',
            "challenge_or_block",
            lambda resp: (
                get_decision(resp) in {"challenge", "block"}
                and "generic_secret" in (get_trace(resp).get("hanuman_detected_secrets") or [])
            ),
        ),
        (
            "AWS access key",
            'AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"',
            "challenge_or_block",
            lambda resp: (
                get_decision(resp) in {"monitor", "challenge", "block"}
                and "aws_access_key" in (get_trace(resp).get("hanuman_detected_secrets") or [])
            ),
        ),
        (
            "Private key critical",
            "-----BEGIN PRIVATE KEY-----\nABCDEF\n-----END PRIVATE KEY-----",
            "block",
            lambda resp: (
                get_decision(resp) == "block"
                and (get_trace(resp).get("secret_severity") == "critical")
                and "private_key" in (get_trace(resp).get("hanuman_detected_secrets") or [])
            ),
        ),
    ]

    for name, text, expected, checker in cases:
        try:
            resp = post_text(text, token=token)
            trace = get_trace(resp)
            passed = checker(resp)
            notes = (
                f"secrets={trace.get('hanuman_detected_secrets')}, "
                f"dangerous={trace.get('hanuman_detected_dangerous_functions')}, "
                f"secret_severity={trace.get('secret_severity')}, "
                f"code_risk={trace.get('hanuman_code_risk_hint')}"
            )
            results.append(TestResult(
                phase="3.2",
                area="code_security",
                name=name,
                expected=expected,
                passed=passed,
                decision=get_decision(resp),
                score=get_score(resp),
                notes=notes,
                response_excerpt=short_json(trace, 250),
            ))
        except Exception as e:
            results.append(TestResult(
                phase="3.2",
                area="code_security",
                name=name,
                expected=expected,
                passed=False,
                notes=f"Exception: {e}",
            ))


def run_phase_33_ocr(results: List[TestResult], token: Optional[str]) -> None:
    img_path = PROJECT_ROOT / "test_screenshot.png"
    maybe_make_screenshot(img_path)

    if not img_path.exists():
        results.append(TestResult(
            phase="3.3",
            area="ocr",
            name="OCR screenshot secret detection",
            expected="block_with_ocr",
            passed=False,
            notes="test_screenshot.png missing and could not be generated",
        ))
        return

    try:
        resp = post_file(img_path, token=token)
        trace = get_trace(resp)
        passed = (
            get_decision(resp) == "block"
            and trace.get("ocr_used") is True
            and trace.get("ocr_text_found") is True
            and "generic_secret" in (trace.get("hanuman_detected_secrets") or [])
        )
        notes = (
            f"ocr_used={trace.get('ocr_used')}, "
            f"ocr_text_found={trace.get('ocr_text_found')}, "
            f"ocr_text_length={trace.get('ocr_text_length')}, "
            f"normalized_text={trace.get('normalized_text')}"
        )
        results.append(TestResult(
            phase="3.3",
            area="ocr",
            name="OCR screenshot secret detection",
            expected="block_with_ocr",
            passed=passed,
            decision=get_decision(resp),
            score=get_score(resp),
            notes=notes,
            response_excerpt=short_json(trace, 250),
        ))
    except Exception as e:
        results.append(TestResult(
            phase="3.3",
            area="ocr",
            name="OCR screenshot secret detection",
            expected="block_with_ocr",
            passed=False,
            notes=f"Exception: {e}",
        ))


def run_phase_34_classification(results: List[TestResult], token: Optional[str]) -> None:
    cases = [
        (
            "PII + finance classification",
            "My email is user@example.com and my credit card is 4111-1111-1111-1111",
            lambda trace: (
                trace.get("sensitivity_label") in {"HIGH", "RESTRICTED"}
                and "pii" in (trace.get("data_categories") or [])
                and "financial" in (trace.get("data_categories") or [])
                and "email" in (trace.get("pii_types") or [])
                and "credit_card" in (trace.get("finance_types") or [])
            ),
        ),
    ]

    for name, text, checker in cases:
        try:
            resp = post_text(text, token=token)
            trace = get_trace(resp)
            passed = checker(trace)
            notes = (
                f"sensitivity={trace.get('sensitivity_label')}, "
                f"data_categories={trace.get('data_categories')}, "
                f"pii_types={trace.get('pii_types')}, "
                f"finance_types={trace.get('finance_types')}"
            )
            results.append(TestResult(
                phase="3.4",
                area="data_classification",
                name=name,
                expected="high_with_pii_and_financial",
                passed=passed,
                decision=get_decision(resp),
                score=get_score(resp),
                notes=notes,
                response_excerpt=short_json(trace, 250),
            ))
        except Exception as e:
            results.append(TestResult(
                phase="3.4",
                area="data_classification",
                name=name,
                expected="high_with_pii_and_financial",
                passed=False,
                notes=f"Exception: {e}",
            ))


def run_phase_35_rag(results: List[TestResult]) -> None:
    rag_script = PROJECT_ROOT / "scripts" / "test_rag_full.py"
    if not rag_script.exists():
        results.append(TestResult(
            phase="3.5",
            area="rag_protection",
            name="RAG full test script",
            expected="script_present_and_passes",
            passed=False,
            notes="scripts/test_rag_full.py not found",
        ))
        return

    try:
        proc = subprocess.run(
            [sys.executable, str(rag_script)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=90,
        )
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        passed = (
            "Retrieval filtering" in output
            and "Output leakage scan" in output
            and (
                "recommended_action': 'block'" in output
                or "action=block" in output
                or "action=redact" in output
            )
        )
        results.append(TestResult(
            phase="3.5",
            area="rag_protection",
            name="RAG full test script",
            expected="retrieval_filtering_and_leakage_scan",
            passed=passed and proc.returncode == 0,
            decision=None,
            score=None,
            notes=f"returncode={proc.returncode}",
            response_excerpt=output[:500] + ("..." if len(output) > 500 else ""),
        ))
    except Exception as e:
        results.append(TestResult(
            phase="3.5",
            area="rag_protection",
            name="RAG full test script",
            expected="retrieval_filtering_and_leakage_scan",
            passed=False,
            notes=f"Exception: {e}",
        ))


def print_summary(results: List[TestResult]) -> None:
    print("\n" + "=" * 100)
    print("GARUDA PHASE 3 FULL VALIDATION SUMMARY")
    print("=" * 100)

    current_phase = None
    for r in results:
        if r.phase != current_phase:
            current_phase = r.phase
            print(f"\n[{current_phase}]")
        status = "PASS" if r.passed else "FAIL"
        print(f"- {status:4} | {r.area:18} | {r.name}")
        if r.notes:
            print(f"       notes: {r.notes}")
        if r.decision is not None:
            print(f"       decision={r.decision}, score={r.score}")

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    print("\n" + "-" * 100)
    print(f"TOTAL: {passed}/{total} passed ({(passed / total * 100):.1f}%)" if total else "TOTAL: 0/0")
    print("-" * 100)


def save_results(results: List[TestResult]) -> None:
    out_json = TEST_RESULTS_DIR / "phase3_full_results.json"
    out_csv = TEST_RESULTS_DIR / "phase3_full_results.csv"

    with out_json.open("w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, indent=2, ensure_ascii=False)

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(results[0]).keys()) if results else [
            "phase", "area", "name", "expected", "passed", "decision", "score", "notes", "response_excerpt"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))

    print(f"\nSaved:")
    print(f"  JSON -> {out_json}")
    print(f"  CSV  -> {out_csv}")


def maybe_login() -> Optional[str]:
    """
    Optional auth login. If auth is not configured or login fails, script continues unauthenticated.
    """
    login_url = f"{API_BASE}/auth/login"
    candidates = [
        {"email": "admin@garuda.local", "password": "admin123"},
        {"email": "admin@example.com", "password": "admin123"},
        {"email": "analyst@example.com", "password": "analyst123"},
    ]
    for cred in candidates:
        try:
            resp = requests.post(login_url, json=cred, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("access_token")
                if token:
                    print(f"[auth] logged in as {cred['email']}")
                    return token
        except Exception:
            pass
    print("[auth] login not available or failed; continuing without token")
    return None


def main() -> None:
    print("Garuda Phase 3 Full Validation")
    print("=" * 100)
    print(f"API base: {API_BASE}")
    token = maybe_login()

    results: List[TestResult] = []

    run_phase_31_files(results, token)
    run_phase_32_code(results, token)
    run_phase_33_ocr(results, token)
    run_phase_34_classification(results, token)
    run_phase_35_rag(results)

    print_summary(results)
    save_results(results)


if __name__ == "__main__":
    main()