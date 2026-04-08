#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib
import json
from pathlib import Path

def sha256_file(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()

def main():
    base = Path.cwd()
    artifacts = {}
    files_to_check = [
        "src/engines/arjuna/arjuna_model.pkl",
        "src/engines/arjuna/arjuna_vectorizer.pkl",
        "src/engines/arjuna/arjuna_label_map.json",
        "src/engines/bhishma/rules.yaml",
        "src/engines/shakuni/rules.yaml",
        "configs/resilience.yaml",
        "configs/integrity.yaml",
    ]
    for rel in files_to_check:
        full = base / rel
        if full.exists():
            artifacts[rel] = {"sha256": sha256_file(full), "size": full.stat().st_size}
        else:
            print(f"Warning: {rel} not found")
    manifest = {"artifacts": artifacts}
    out = base / "configs/trusted_artifacts.json"
    with open(out, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"Written {out} with {len(artifacts)} entries.")

if __name__ == "__main__":
    main()
