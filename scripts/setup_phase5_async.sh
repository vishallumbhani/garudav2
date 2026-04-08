#!/bin/bash
set -e
cd ~/garuda

mkdir -p src/resilience src/protection src/playbooks configs scripts

touch src/resilience/__init__.py src/protection/__init__.py src/playbooks/__init__.py

# Health tracker (async)
cat > src/resilience/health.py << 'EOF'
"""Async engine health tracking."""
from enum import Enum
from datetime import datetime
from typing import Dict, Optional
import asyncio

class EngineState(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    TRIPPED = "tripped"
    DISABLED = "disabled"

class EngineHealth:
    def __init__(self, name: str):
        self.name = name
        self.state = EngineState.HEALTHY
        self.last_success: Optional[datetime] = None
        self.last_failure: Optional[datetime] = None
        self.consecutive_failures = 0
        self.fallback_count = 0
        self._lock = asyncio.Lock()

    async def record_success(self):
        async with self._lock:
            self.state = EngineState.HEALTHY
            self.last_success = datetime.utcnow()
            self.consecutive_failures = 0

    async def record_failure(self):
        async with self._lock:
            self.consecutive_failures += 1
            self.last_failure = datetime.utcnow()
            if self.consecutive_failures >= 3:
                self.state = EngineState.TRIPPED

    async def reset(self):
        async with self._lock:
            self.state = EngineState.HEALTHY
            self.consecutive_failures = 0

_engine_health: Dict[str, EngineHealth] = {}

def get_health(engine_name: str) -> EngineHealth:
    if engine_name not in _engine_health:
        _engine_health[engine_name] = EngineHealth(engine_name)
    return _engine_health[engine_name]
EOF

# Circuit breaker (async)
cat > src/resilience/circuit_breaker.py << 'EOF'
import time
import asyncio
from typing import Dict

class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 3, timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = asyncio.Lock()

    async def is_open(self) -> bool:
        async with self._lock:
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.timeout:
                    self.state = "HALF_OPEN"
                    return False
                return True
            return False

    async def record_success(self):
        async with self._lock:
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
            self.failures = 0

    async def record_failure(self):
        async with self._lock:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"

_breakers: Dict[str, CircuitBreaker] = {}

def get_breaker(name: str) -> CircuitBreaker:
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name)
    return _breakers[name]
EOF

# Severity mapping
cat > src/playbooks/severity.py << 'EOF'
from enum import IntEnum

class Severity(IntEnum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

def map_severity(failure_type: str, engine_status: dict = None, suspicious_input: bool = False) -> Severity:
    if "tampering" in failure_type.lower() or "manifest" in failure_type.lower():
        return Severity.CRITICAL
    if "checksum" in failure_type.lower() or "injection" in failure_type.lower():
        return Severity.HIGH
    if "degraded" in str(engine_status) or "extractor" in failure_type.lower():
        return Severity.MEDIUM
    return Severity.LOW
EOF

# Integrity check (synchronous – run at startup)
cat > src/protection/integrity.py << 'EOF'
import hashlib
import json
from pathlib import Path
from typing import Tuple, List

CRITICAL_PATHS = [
    "src/engines/arjuna/arjuna_model.pkl",
    "src/engines/arjuna/arjuna_vectorizer.pkl",
    "src/engines/arjuna/arjuna_label_map.json",
    "src/engines/bhishma/rules.yaml",
    "src/engines/shakuni/rules.yaml",
    "configs/resilience.yaml",
    "configs/integrity.yaml",
]

def compute_sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()

def verify_integrity(manifest_path: Path = Path("configs/trusted_artifacts.json")) -> Tuple[bool, List[str]]:
    if not manifest_path.exists():
        return False, ["trusted_artifacts.json missing"]
    with open(manifest_path) as f:
        manifest = json.load(f)
    failures = []
    for rel_path, expected in manifest.get("artifacts", {}).items():
        full = Path(rel_path)
        if not full.exists():
            failures.append(f"{rel_path} missing")
            continue
        actual = compute_sha256(full)
        if actual != expected.get("sha256"):
            failures.append(f"{rel_path} checksum mismatch")
    return len(failures) == 0, failures
EOF

# Create default configs
cat > configs/resilience.yaml << 'EOF'
circuit_breaker:
  failure_threshold: 3
  open_timeout_seconds: 60

degraded_mode:
  fallback_engines: ["bhishma", "shakuni"]
  disable_redis_on_error: true
EOF

cat > configs/integrity.yaml << 'EOF'
startup:
  fail_on_critical_missing: false
  fail_on_checksum_mismatch: false
EOF

echo "Phase 5 async structure created."