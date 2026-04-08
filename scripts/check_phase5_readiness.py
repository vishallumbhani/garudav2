#!/usr/bin/env python3
"""
Phase 5 Readiness Audit for Garuda
Checks what exists today vs what is needed for:

5.1 Rakshak self-protection
5.2 Resilience framework
5.3 Chaos and fault testing
5.4 Response playbooks

Usage:
    python scripts/check_phase5_readiness.py
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Tuple


ROOT = Path(__file__).resolve().parent.parent


@dataclass
class CheckResult:
    phase: str
    control: str
    status: str   # PRESENT / PARTIAL / MISSING
    evidence: List[str]
    notes: str


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def file_exists(rel_path: str) -> bool:
    return (ROOT / rel_path).exists()


def find_paths(start_rel: str, pattern: str) -> List[str]:
    base = ROOT / start_rel
    if not base.exists():
        return []
    return [str(p.relative_to(ROOT)) for p in base.rglob(pattern)]


def grep_in_files(rel_paths: List[str], patterns: List[str]) -> Tuple[List[str], List[str]]:
    matched_files = []
    matched_snippets = []

    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]

    for rel_path in rel_paths:
        path = ROOT / rel_path
        if not path.exists() or not path.is_file():
            continue

        text = read_text(path)
        if not text:
            continue

        file_matched = False
        for rgx in compiled:
            m = rgx.search(text)
            if m:
                file_matched = True
                snippet = text[max(0, m.start() - 60): min(len(text), m.end() + 120)]
                matched_snippets.append(f"{rel_path}: ...{snippet.replace(chr(10), ' ')}...")
        if file_matched:
            matched_files.append(rel_path)

    return matched_files, matched_snippets


def evaluate_presence(
    files_found: List[str],
    matched_files: List[str],
    min_file_presence: int = 1,
    min_match_presence: int = 1,
) -> str:
    if len(files_found) >= min_file_presence and len(matched_files) >= min_match_presence:
        return "PRESENT"
    if files_found or matched_files:
        return "PARTIAL"
    return "MISSING"


def collect_python_files() -> List[str]:
    src_dir = ROOT / "src"
    files = []
    if src_dir.exists():
        files.extend([str(p.relative_to(ROOT)) for p in src_dir.rglob("*.py")])
    return sorted(files)


def collect_yaml_json_files() -> List[str]:
    out = []
    for folder in ["configs", "src", "deploy"]:
        base = ROOT / folder
        if base.exists():
            for ext in ("*.yaml", "*.yml", "*.json"):
                out.extend([str(p.relative_to(ROOT)) for p in base.rglob(ext)])
    return sorted(set(out))


def check_config_integrity() -> CheckResult:
    candidate_files = collect_python_files() + collect_yaml_json_files()
    patterns = [
        r"sha256",
        r"hashlib",
        r"checksum",
        r"integrity",
        r"trusted_artifacts",
        r"manifest",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = [p for p in candidate_files if "config" in p.lower() or "integrity" in p.lower()]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.1",
        control="config integrity checks",
        status=status,
        evidence=(matched_files[:5] + files_found[:5]),
        notes="Need startup validation of configs/models/rules and trusted hash verification."
    )


def check_model_rule_checksums() -> CheckResult:
    artifacts = [
        "src/engines/arjuna/arjuna_model.pkl",
        "src/engines/arjuna/arjuna_vectorizer.pkl",
        "src/engines/arjuna/arjuna_label_map.json",
        "src/engines/bhishma/rules.yaml",
        "src/engines/shakuni/rules.yaml",
    ]
    existing_artifacts = [p for p in artifacts if file_exists(p)]

    candidate_files = collect_python_files() + collect_yaml_json_files()
    patterns = [
        r"sha256",
        r"checksum",
        r"hashlib",
        r"model.*hash",
        r"rules?.*hash",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)

    if existing_artifacts and matched_files:
        status = "PARTIAL" if not file_exists("configs/trusted_artifacts.json") else "PRESENT"
    elif existing_artifacts:
        status = "PARTIAL"
    else:
        status = "MISSING"

    return CheckResult(
        phase="5.1",
        control="model/rule checksum checks",
        status=status,
        evidence=existing_artifacts[:5] + matched_files[:5],
        notes="Models/rules exist, but checksum manifest enforcement should be explicit."
    )


def check_signed_artifact_strategy() -> CheckResult:
    candidate_files = collect_python_files() + collect_yaml_json_files()
    patterns = [
        r"signature",
        r"signed",
        r"hmac",
        r"sigstore",
        r"gpg",
        r"artifact_sign",
        r"manifest",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = [p for p in candidate_files if "sign" in p.lower() or "manifest" in p.lower()]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.1",
        control="signed artifact strategy",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="Recommended: signed manifest for critical artifacts, validated at startup."
    )


def check_secret_protection() -> CheckResult:
    candidate_files = collect_python_files()
    patterns = [
        r"os\.environ",
        r"getenv",
        r"secret",
        r"api[_-]?key",
        r"jwt",
        r"password",
        r"token",
        r"redact",
        r"mask",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = [
        p for p in candidate_files
        if any(x in p.lower() for x in ["auth", "config", "jwt", "api_key", "secret"])
    ]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.1",
        control="secret protection",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="Need secret validation + prevention of secret leakage in logs and traces."
    )


def check_log_integrity() -> CheckResult:
    candidate_files = collect_python_files()
    patterns = [
        r"audit",
        r"jsonl",
        r"log",
        r"hash.*chain",
        r"prev_hash",
        r"log_integrity",
        r"tamper",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = []
    for p in ["logs/audit.jsonl", "src/services/audit_service.py", "src/api/routes/audit.py"]:
        if file_exists(p):
            files_found.append(p)

    if files_found and matched_files:
        status = "PARTIAL"
    elif files_found:
        status = "PARTIAL"
    else:
        status = "MISSING"

    return CheckResult(
        phase="5.1",
        control="log integrity",
        status=status,
        evidence=files_found[:5] + matched_files[:5],
        notes="Audit logging exists, but hash-chain or tamper-evident integrity may still be missing."
    )


def check_engine_health_model() -> CheckResult:
    candidate_files = collect_python_files()
    patterns = [
        r"health",
        r"status",
        r"degraded",
        r"fallback_used",
        r"degraded_engines",
        r"engine_results",
        r"latency",
        r"timeout",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = [p for p in candidate_files if "health" in p.lower() or "fallback" in p.lower()]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.2",
        control="engine health model",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="Need explicit per-engine health tracking: success/failure/latency/consecutive failures."
    )


def check_circuit_breaker() -> CheckResult:
    candidate_files = collect_python_files()
    patterns = [
        r"circuit.?breaker",
        r"open.*breaker",
        r"half.?open",
        r"consecutive failures",
        r"trip",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = [p for p in candidate_files if "circuit" in p.lower() or "breaker" in p.lower()]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.2",
        control="circuit breaker logic",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="Should explicitly guard repeated engine failures and allow recovery probes."
    )


def check_retry_policy() -> CheckResult:
    candidate_files = collect_python_files()
    patterns = [
        r"retry",
        r"backoff",
        r"sleep",
        r"attempt",
        r"max_retries",
        r"exponential",
        r"jitter",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = [p for p in candidate_files if "retry" in p.lower()]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.2",
        control="retry policy",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="Transient failures should retry with bounded backoff and timeout budget."
    )


def check_degraded_mode() -> CheckResult:
    candidate_files = collect_python_files()
    patterns = [
        r"degraded",
        r"fallback_used",
        r"degraded_engines",
        r"status.*degraded",
        r"fallback",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = [p for p in candidate_files if "fallback" in p.lower() or "degraded" in p.lower()]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.2",
        control="degraded mode",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="This appears likely present in some form; validate whether it is formalized consistently."
    )


def check_safe_mode() -> CheckResult:
    candidate_files = collect_python_files()
    patterns = [
        r"safe_mode",
        r"safe mode",
        r"fail.?closed",
        r"trust failure",
        r"integrity.*failed",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = [p for p in candidate_files if "safe_mode" in p.lower()]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.2",
        control="safe mode",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="Recommended to activate on integrity failure or multi-critical-engine degradation."
    )


def check_failure_injection() -> CheckResult:
    candidate_files = collect_python_files()
    test_files = find_paths("scripts", "test*.py") + find_paths("src/tests", "test*.py")
    patterns = [
        r"failure injection",
        r"simulate",
        r"rename",
        r"missing model",
        r"missing rules",
        r"chaos",
        r"fault",
    ]
    matched_files, snippets = grep_in_files(test_files + candidate_files, patterns)
    files_found = [p for p in test_files if any(x in p.lower() for x in ["failure", "fault", "chaos"])]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.3",
        control="engine failure injection",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="You likely already have some failure-injection testing; formalize it under Phase 5."
    )


def check_db_failure_cases() -> CheckResult:
    candidate_files = collect_python_files()
    patterns = [
        r"sqlalchemy",
        r"commit",
        r"rollback",
        r"db.*fail",
        r"database.*error",
        r"except",
        r"persist_audit",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = [p for p in candidate_files if "/db/" in p or "audit_service" in p or "scan_service" in p]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.3",
        control="DB failure cases",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="DB integration exists, but explicit DB failure-path tests and local spool fallback may need enhancement."
    )


def check_redis_failure_cases() -> CheckResult:
    candidate_files = collect_python_files()
    patterns = [
        r"redis",
        r"connectionerror",
        r"timeout",
        r"behavior",
        r"threat_memory",
        r"session",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = [p for p in candidate_files if "threat_memory" in p.lower() or "behavior_service" in p.lower()]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.3",
        control="Redis failure cases",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="Behavior/session memory exists; need explicit Redis outage handling and tests."
    )


def check_extractor_failure_cases() -> CheckResult:
    candidate_files = collect_python_files()
    patterns = [
        r"extract",
        r"pdf",
        r"ocr",
        r"docx",
        r"exception",
        r"try:",
        r"unsupported",
        r"corrupt",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = [
        p for p in candidate_files
        if "extractor" in p.lower() or p.endswith("/ocr.py")
    ]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.3",
        control="extractor failure cases",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="Extractors exist; validate corrupt/timeout/parser-failure behavior and quarantine path."
    )


def check_fallback_validation() -> CheckResult:
    candidate_files = collect_python_files()
    test_files = find_paths("scripts", "test*.py") + find_paths("src/tests", "test*.py")
    patterns = [
        r"fallback_used",
        r"degraded_engines",
        r"status.*degraded",
        r"decision_logic",
        r"fallback",
    ]
    matched_files, snippets = grep_in_files(candidate_files + test_files, patterns)
    files_found = [p for p in candidate_files if "fallback" in p.lower()]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.3",
        control="fallback validation",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="Looks likely present in some form; validate exact fallback trust rules and tests."
    )


def check_alerting() -> CheckResult:
    candidate_files = collect_python_files()
    patterns = [
        r"send_alert",
        r"alert",
        r"severity",
        r"incident",
        r"title",
        r"description",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = [p for p in candidate_files if "alert" in p.lower()]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.4",
        control="alerting",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="This appears to exist already."
    )


def check_throttle() -> CheckResult:
    candidate_files = collect_python_files()
    patterns = [
        r"throttle",
        r"rate limit",
        r"cooldown",
        r"backoff",
        r"slowdown",
        r"abuse",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = [p for p in candidate_files if "throttle" in p.lower() or "rate" in p.lower()]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.4",
        control="throttle",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="Likely missing unless you have explicit session/API-key abuse throttling."
    )


def check_quarantine() -> CheckResult:
    candidate_files = collect_python_files()
    patterns = [
        r"quarantine",
        r"data/quarantine",
        r"move",
        r"copy",
        r"suspicious file",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = []
    if file_exists("data/quarantine"):
        files_found.append("data/quarantine")
    files_found.extend([p for p in candidate_files if "quarantine" in p.lower()])
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.4",
        control="quarantine",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="Quarantine folder exists; validate code path that moves/marks suspicious files."
    )


def check_isolate_session() -> CheckResult:
    candidate_files = collect_python_files()
    patterns = [
        r"isolate",
        r"session",
        r"threat_memory",
        r"family repeats",
        r"high_risk_count",
        r"session_floor",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = [
        p for p in candidate_files
        if "threat_memory" in p.lower() or "behavior_service" in p.lower()
    ]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.4",
        control="isolate session",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="Session-based escalation exists; explicit isolation playbook may still need to be formalized."
    )


def check_incident_severity_mapping() -> CheckResult:
    candidate_files = collect_python_files()
    patterns = [
        r"severity",
        r"severity_mapping",
        r"incident",
        r"priority",
        r"sev[1-4]",
        r"alert",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = [p for p in candidate_files if "severity" in p.lower()]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="5.4",
        control="incident severity mapping",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="Alerting with severity may exist; central severity mapping module may still be missing."
    )


def check_critical_gap_decision_guard() -> CheckResult:
    candidate_files = collect_python_files()
    patterns = [
        r"decision_guard",
        r"decision floor",
        r"safe_mode",
        r"fallback_used",
        r"degraded_engines",
        r"raise minimum decision",
        r"trust penalty",
        r"final decision cannot be allow",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)
    files_found = [p for p in candidate_files if "decision_guard" in p.lower()]
    status = evaluate_presence(files_found, matched_files)
    return CheckResult(
        phase="GAP",
        control="failure-aware decision override layer",
        status=status,
        evidence=matched_files[:5] + files_found[:5],
        notes="Critical gap: a formal decision guard should constrain final decisions when trust is degraded."
    )


def check_pipeline_execution_order() -> CheckResult:
    candidate_files = [
        "src/services/scan_service.py",
        "src/core/fallback.py",
        "src/services/audit_service.py",
        "src/core/config.py",
    ]
    candidate_files = [p for p in candidate_files if file_exists(p)]

    patterns = [
        r"integrity",
        r"health",
        r"fallback",
        r"decision",
        r"policy",
        r"audit",
        r"alert",
        r"severity",
    ]
    matched_files, snippets = grep_in_files(candidate_files, patterns)

    text = ""
    for p in candidate_files:
        text += "\n" + read_text(ROOT / p)

    has_scan = "scan_text" in text or "scan_file" in text
    has_decision = re.search(r"decision", text, re.IGNORECASE) is not None
    has_policy = re.search(r"policy", text, re.IGNORECASE) is not None
    has_audit = re.search(r"audit", text, re.IGNORECASE) is not None
    has_integrity = re.search(r"integrity", text, re.IGNORECASE) is not None
    has_health = re.search(r"health", text, re.IGNORECASE) is not None

    if has_scan and has_decision and has_policy and has_audit and has_integrity and has_health:
        status = "PARTIAL"
    elif has_scan and has_decision and has_policy and has_audit:
        status = "PARTIAL"
    else:
        status = "MISSING"

    return CheckResult(
        phase="PIPELINE",
        control="execution order integration",
        status=status,
        evidence=matched_files[:8],
        notes=(
            "Need formal pipeline order: normalize -> integrity -> health -> engines -> "
            "resilience -> base decision -> decision guard -> policy -> playbooks -> audit"
        ),
    )


def summarize(results: List[CheckResult]) -> Dict[str, int]:
    summary = {"PRESENT": 0, "PARTIAL": 0, "MISSING": 0}
    for r in results:
        summary[r.status] = summary.get(r.status, 0) + 1
    return summary


def print_report(results: List[CheckResult]) -> None:
    print("=" * 100)
    print("GARUDA PHASE 5 READINESS AUDIT")
    print("=" * 100)

    current_phase = None
    for r in results:
        if r.phase != current_phase:
            current_phase = r.phase
            print(f"\n[{current_phase}]")
        print(f"- {r.status:<7} | {r.control}")
        if r.evidence:
            for ev in r.evidence[:3]:
                print(f"    evidence: {ev}")
        print(f"    notes: {r.notes}")

    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    s = summarize(results)
    print(json.dumps(s, indent=2))

    print("\n" + "=" * 100)
    print("PRIORITY ENHANCEMENTS")
    print("=" * 100)

    missing_or_partial = [r for r in results if r.status in ("MISSING", "PARTIAL")]
    priority_order = [
        "failure-aware decision override layer",
        "execution order integration",
        "config integrity checks",
        "model/rule checksum checks",
        "engine health model",
        "circuit breaker logic",
        "retry policy",
        "safe mode",
        "incident severity mapping",
        "throttle",
        "quarantine",
    ]

    ordered = []
    used = set()
    for name in priority_order:
        for r in missing_or_partial:
            if r.control == name and r.control not in used:
                ordered.append(r)
                used.add(r.control)

    for r in missing_or_partial:
        if r.control not in used:
            ordered.append(r)
            used.add(r.control)

    for idx, r in enumerate(ordered[:12], start=1):
        print(f"{idx}. [{r.status}] {r.phase} - {r.control}")
        print(f"   {r.notes}")

    out_dir = ROOT / "test_results"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "phase5_readiness_report.json"
    txt_path = out_dir / "phase5_readiness_report.txt"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, indent=2)

    with txt_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(f"[{r.phase}] {r.control} -> {r.status}\n")
            for ev in r.evidence:
                f.write(f"  evidence: {ev}\n")
            f.write(f"  notes: {r.notes}\n\n")

    print("\nReports written:")
    print(f"- {json_path}")
    print(f"- {txt_path}")


def main() -> None:
    results = [
        check_config_integrity(),
        check_model_rule_checksums(),
        check_signed_artifact_strategy(),
        check_secret_protection(),
        check_log_integrity(),
        check_engine_health_model(),
        check_circuit_breaker(),
        check_retry_policy(),
        check_degraded_mode(),
        check_safe_mode(),
        check_failure_injection(),
        check_db_failure_cases(),
        check_redis_failure_cases(),
        check_extractor_failure_cases(),
        check_fallback_validation(),
        check_alerting(),
        check_throttle(),
        check_quarantine(),
        check_isolate_session(),
        check_incident_severity_mapping(),
        check_critical_gap_decision_guard(),
        check_pipeline_execution_order(),
    ]
    print_report(results)


if __name__ == "__main__":
    main()