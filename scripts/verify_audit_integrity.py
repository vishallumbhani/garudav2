#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

def verify_audit_chain(log_path=Path("logs/audit.jsonl")):
    if not log_path.exists():
        print("No audit log found.")
        return True
    prev_hash = None
    first_valid = None
    valid_entries = 0
    with open(log_path) as f:
        for i, line in enumerate(f, 1):
            try:
                entry = json.loads(line)
                if "prev_hash" not in entry:
                    print(f"Line {i}: missing prev_hash (old entry, skipping)")
                    continue
                valid_entries += 1
                if first_valid is None:
                    first_valid = i
                if prev_hash is not None and entry["prev_hash"] != prev_hash:
                    print(f"Line {i}: hash mismatch (expected {prev_hash}, got {entry['prev_hash']})")
                    return False
                # Compute hash of this line (excluding newline)
                prev_hash = hashlib.sha256(line.rstrip('\n').encode()).hexdigest()
            except Exception as e:
                print(f"Line {i}: error {e}")
                return False
    if valid_entries == 0:
        print("No entries with prev_hash found. Audit integrity not verifiable (old log).")
        return True
    print(f"Audit log integrity verified for {valid_entries} entries (starting line {first_valid}).")
    return True

if __name__ == "__main__":
    verify_audit_chain()
