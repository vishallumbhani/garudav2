import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Tuple, List, Dict, Any

from src.core.fallback import fallback

CRITICAL_PATHS = [
    "src/engines/arjuna/arjuna_model.pkl",
    "src/engines/arjuna/arjuna_vectorizer.pkl",
    "src/engines/arjuna/arjuna_label_map.json",
    "src/engines/bhishma/rules.yaml",
    "src/engines/shakuni/rules.yaml",
    "configs/resilience.yaml",
    "configs/integrity.yaml",
]

MANIFEST_PATH = Path("configs/trusted_artifacts.json")
SIGNATURE_PATH = Path("configs/trusted_artifacts.sig")


def compute_sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _canonical_manifest_bytes(manifest: Dict[str, Any]) -> bytes:
    return json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_manifest_signature(manifest: Dict[str, Any], signing_key: str) -> str:
    return hmac.new(
        signing_key.encode("utf-8"),
        _canonical_manifest_bytes(manifest),
        hashlib.sha256,
    ).hexdigest()


def verify_manifest_signature(
    manifest: Dict[str, Any],
    signature: str,
    signing_key: str,
) -> bool:
    expected = compute_manifest_signature(manifest, signing_key)
    return hmac.compare_digest(expected, signature.strip())


def verify_integrity(
    manifest_path: Path = MANIFEST_PATH,
) -> Tuple[bool, List[str], List[str]]:
    """
    Returns:
        (ok, failures, artifacts_checked)
    """
    if not manifest_path.exists():
        return False, ["trusted_artifacts.json missing"], []

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    failures: List[str] = []
    artifacts_checked: List[str] = []

    artifacts = manifest.get("artifacts", {})
    if not isinstance(artifacts, dict) or not artifacts:
        return False, ["trusted_artifacts.json has no artifacts"], []

    for rel_path, expected in artifacts.items():
        artifacts_checked.append(rel_path)
        full = Path(rel_path)

        if not full.exists():
            failures.append(f"{rel_path} missing")
            continue

        actual_sha = compute_sha256(full)
        expected_sha = expected.get("sha256")
        if actual_sha != expected_sha:
            failures.append(f"{rel_path} checksum mismatch")

    return len(failures) == 0, failures, artifacts_checked


def verify_signed_artifacts(
    manifest_path: Path = MANIFEST_PATH,
    signature_path: Path = SIGNATURE_PATH,
) -> Tuple[bool, List[str], List[str]]:
    """
    Returns:
        (ok, failures, artifacts_checked)
    """
    failures: List[str] = []
    artifacts_checked: List[str] = []

    if not manifest_path.exists():
        return False, ["trusted_artifacts.json missing"], []

    if not signature_path.exists():
        return False, ["trusted_artifacts.sig missing"], []

    signing_key = os.getenv("GARUDA_ARTIFACT_SIGNING_KEY")
    if not signing_key:
        return False, ["GARUDA_ARTIFACT_SIGNING_KEY missing"], []

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    with open(signature_path, "r", encoding="utf-8") as f:
        signature = f.read().strip()

    if not verify_manifest_signature(manifest, signature, signing_key):
        return False, ["trusted_artifacts.sig invalid"], []

    ok, integrity_failures, artifacts_checked = verify_integrity(manifest_path)
    failures.extend(integrity_failures)

    return ok and not failures, failures, artifacts_checked


def run_integrity_precheck(request=None) -> Dict[str, Any]:
    """
    Runtime integrity check:
    1. verify manifest signature
    2. verify current artifact hashes
    3. surface failures to safe mode / decision guard
    """
    ok, failures, artifacts_checked = verify_signed_artifacts()

    # include any fallback-tracked integrity failures too
    runtime_failures = list(fallback.integrity_failures or [])
    all_failures = failures + runtime_failures

    if all_failures:
        return {
            "status": "failed",
            "safe_mode_required": True,
            "reasons": all_failures,
            "artifacts_checked": artifacts_checked,
        }

    return {
        "status": "ok",
        "safe_mode_required": False,
        "reasons": [],
        "artifacts_checked": artifacts_checked,
    }