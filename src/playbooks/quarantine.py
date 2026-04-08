import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

QUARANTINE_DIR = Path("data/quarantine")
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

def quarantine_file(original_path: Path, reason: str, metadata: Optional[dict] = None) -> Path:
    """
    Move a suspicious file to quarantine with metadata.
    Returns the new quarantine path.
    """
    if not original_path.exists():
        raise FileNotFoundError(f"File not found: {original_path}")

    # Create a safe name: original name + timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{original_path.stem}_{timestamp}{original_path.suffix}"
    dest = QUARANTINE_DIR / safe_name

    # Move file
    shutil.move(str(original_path), str(dest))

    # Write metadata
    meta_path = dest.with_suffix(".meta.json")
    meta = {
        "original_path": str(original_path),
        "quarantined_at": timestamp,
        "reason": reason,
        "metadata": metadata or {},
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    return dest