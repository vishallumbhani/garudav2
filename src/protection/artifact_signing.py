import hashlib
import hmac
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

ROOT = Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json_bytes(data: Dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_manifest(manifest: Dict[str, Any], secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), canonical_json_bytes(manifest), hashlib.sha256).hexdigest()


def verify_manifest_signature(manifest: Dict[str, Any], signature: str, secret: str) -> bool:
    expected = sign_manifest(manifest, secret)
    return hmac.compare_digest(expected, signature.strip())


def verify_artifacts(manifest: Dict[str, Any]) -> Tuple[bool, List[str]]:
    failures: List[str] = []

    for item in manifest.get("artifacts", []):
        rel_path = item.get("path")
        expected_hash = item.get("sha256")
        if not rel_path or not expected_hash:
            failures.append(f"invalid manifest entry: {item}")
            continue

        full_path = ROOT / rel_path
        if not full_path.exists():
            failures.append(f"missing artifact: {rel_path}")
            continue

        actual_hash = sha256_file(full_path)
        if actual_hash != expected_hash:
            failures.append(
                f"hash mismatch: {rel_path} expected={expected_hash} actual={actual_hash}"
            )

    return len(failures) == 0, failures