#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import os
from pathlib import Path

SECRET_KEY = os.environ.get("GARUDA_SIGNING_SECRET", "change-me-in-production")
MANIFEST_PATH = Path("configs/trusted_artifacts.json")

def compute_sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()

def sign_data(data: str) -> str:
    return hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()

def main():
    base = Path.cwd()
    artifacts = {}
    files_to_sign = [
        "src/engines/arjuna/arjuna_model.pkl",
        "src/engines/arjuna/arjuna_vectorizer.pkl",
        "src/engines/arjuna/arjuna_label_map.json",
        "src/engines/bhishma/rules.yaml",
        "src/engines/shakuni/rules.yaml",
        "configs/resilience.yaml",
        "configs/integrity.yaml",
    ]
    for rel in files_to_sign:
        full = base / rel
        if full.exists():
            sha = compute_sha256(full)
            artifacts[rel] = {
                "sha256": sha,
                "size": full.stat().st_size,
                "version": "1.0"
            }
        else:
            print(f"Warning: {rel} not found")
    # Create a combined string of all hashes for signing
    combined = "".join(f"{k}:{v['sha256']}" for k, v in sorted(artifacts.items()))
    signature = sign_data(combined)
    manifest = {
        "signature": signature,
        "artifacts": artifacts
    }
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Signed manifest written to {MANIFEST_PATH}")

if __name__ == "__main__":
    main()
