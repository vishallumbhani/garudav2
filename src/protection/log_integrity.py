import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any

AUDIT_LOG_PATH = Path("logs/audit.jsonl")


def _canonical_payload(payload: Dict[str, Any]) -> bytes:
    clean = dict(payload)
    clean.pop("prev_hash", None)
    clean.pop("entry_hash", None)
    return json.dumps(clean, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def compute_prev_hash(audit_log_path: Path = AUDIT_LOG_PATH) -> str:
    """
    Return previous entry_hash from the last audit line.
    If no log exists, return GENESIS.
    """
    if not audit_log_path.exists():
        return "GENESIS"

    last_line: Optional[str] = None
    with open(audit_log_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last_line = line.strip()

    if not last_line:
        return "GENESIS"

    try:
        record = json.loads(last_line)
        return record.get("entry_hash", "GENESIS")
    except Exception:
        return "GENESIS"


def compute_entry_hash(payload: Dict[str, Any], prev_hash: str) -> str:
    sha = hashlib.sha256()
    sha.update(prev_hash.encode("utf-8"))
    sha.update(_canonical_payload(payload))
    return sha.hexdigest()


def add_hash_chain_fields(payload: Dict[str, Any], audit_log_path: Path = AUDIT_LOG_PATH) -> Dict[str, Any]:
    prev_hash = compute_prev_hash(audit_log_path)
    entry_hash = compute_entry_hash(payload, prev_hash)
    enriched = dict(payload)
    enriched["prev_hash"] = prev_hash
    enriched["entry_hash"] = entry_hash
    return enriched


def verify_hash_chain(audit_log_path: Path = AUDIT_LOG_PATH) -> bool:
    if not audit_log_path.exists():
        return True

    expected_prev = "GENESIS"

    with open(audit_log_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue

            record = json.loads(line)
            prev_hash = record.get("prev_hash")
            entry_hash = record.get("entry_hash")

            if prev_hash != expected_prev:
                return False

            calculated = compute_entry_hash(record, prev_hash)
            if calculated != entry_hash:
                return False

            expected_prev = entry_hash

    return True