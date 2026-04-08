#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tempfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.playbooks.quarantine import quarantine_file

def test_quarantine():
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
        f.write("suspicious content")
        path = Path(f.name)
    
    # Quarantine it
    quarantined = quarantine_file(path, reason="test", metadata={"test": True})
    assert not path.exists(), "Original file still exists"
    assert quarantined.exists(), "Quarantined file not found"
    meta_path = quarantined.with_suffix(".meta.json")
    assert meta_path.exists(), "Metadata not created"
    print(f"Quarantine test passed. Quarantined file: {quarantined}")

if __name__ == "__main__":
    test_quarantine()
