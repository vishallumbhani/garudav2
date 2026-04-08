import logging
import time
from typing import Dict, Any, Optional, Set
from pathlib import Path
import json
import hashlib
import os
import hmac

logger = logging.getLogger(__name__)

# ---------- Health & Circuit Breaker (sync) ----------
class EngineHealth:
    __slots__ = ('name', 'last_success', 'last_failure', 'consecutive_failures', 'state')
    def __init__(self, name: str):
        self.name = name
        self.last_success: Optional[float] = None
        self.last_failure: Optional[float] = None
        self.consecutive_failures = 0
        self.state = "healthy"

    def record_success(self):
        self.last_success = time.time()
        self.consecutive_failures = 0
        self.state = "healthy"

    def record_failure(self):
        self.consecutive_failures += 1
        self.last_failure = time.time()
        if self.consecutive_failures >= 3:
            self.state = "tripped"

class CircuitBreaker:
    __slots__ = ('name', 'failure_threshold', 'timeout', 'failures', 'last_failure_time', 'state')
    def __init__(self, name: str, failure_threshold: int = 3, timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"

    def is_open(self) -> bool:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                return False
            return True
        return False

    def record_success(self):
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
        self.failures = 0

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"

_health_registry: Dict[str, EngineHealth] = {}
_breaker_registry: Dict[str, CircuitBreaker] = {}

def _get_health(name: str) -> EngineHealth:
    if name not in _health_registry:
        _health_registry[name] = EngineHealth(name)
    return _health_registry[name]

def _get_breaker(name: str) -> CircuitBreaker:
    if name not in _breaker_registry:
        _breaker_registry[name] = CircuitBreaker(name)
    return _breaker_registry[name]

# ---------- Integrity Helpers ----------
def compute_sha256(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()

def verify_critical_artifacts(manifest_path: Path = Path("configs/trusted_artifacts.json")) -> tuple[bool, list[str]]:
    if not manifest_path.exists():
        return False, ["trusted_artifacts.json missing"]
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except Exception as e:
        return False, [f"manifest parse error: {e}"]
    
    # Verify signature if present
    signature = manifest.get("signature")
    artifacts = manifest.get("artifacts", {})
    if signature:
        combined = "".join(f"{k}:{v.get('sha256','')}" for k, v in sorted(artifacts.items()))
        secret = os.environ.get("GARUDA_SIGNING_SECRET", "change-me-in-production")
        expected = hmac.new(secret.encode(), combined.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False, ["Manifest signature invalid"]
    
    failures = []
    for rel_path, expected in artifacts.items():
        full = Path(rel_path)
        if not full.exists():
            failures.append(f"{rel_path} missing")
            continue
        actual = compute_sha256(full)
        if actual != expected.get("sha256"):
            failures.append(f"{rel_path} checksum mismatch")
    return len(failures) == 0, failures

# ---------- Fallback Manager (Enhanced) ----------
class FallbackManager:
    def __init__(self, safe_mode: bool = True, enable_circuit_breaker: bool = True):
        self.safe_mode = safe_mode
        self.enable_circuit_breaker = enable_circuit_breaker
        self.degraded_engines: Set[str] = set()
        self.integrity_failures: list[str] = []
        self._integrity_checked = False

    def check_integrity_on_startup(self, manifest_path: Path = Path("configs/trusted_artifacts.json")) -> bool:
        ok, failures = verify_critical_artifacts(manifest_path)
        self.integrity_failures = failures
        self._integrity_checked = True
        if not ok:
            logger.critical(f"Integrity check failed: {failures}")
            if self.safe_mode:
                logger.critical("Safe mode enabled due to integrity failure")
        return ok

    def wrap_engine(self, engine_name: str, func, *args, **kwargs) -> Dict[str, Any]:
        health = _get_health(engine_name)
        breaker = _get_breaker(engine_name)

        if self.enable_circuit_breaker and breaker.is_open():
            logger.warning(f"Circuit breaker open for {engine_name}, skipping call")
            self.degraded_engines.add(engine_name)
            return {
                "engine": engine_name,
                "status": "degraded",
                "score": 0.5,
                "confidence": 0.0,
                "labels": ["circuit_open"],
                "reason": f"Circuit breaker open for {engine_name}",
                "error": "circuit_breaker_open"
            }

        try:
            result = func(*args, **kwargs)
            if not isinstance(result, dict):
                raise ValueError(f"Engine {engine_name} returned non-dict")
            result.setdefault("status", "ok")
            health.record_success()
            breaker.record_success()
            self.degraded_engines.discard(engine_name)
            return result
        except Exception as e:
            logger.error(f"Engine {engine_name} failed: {e}")
            health.record_failure()
            breaker.record_failure()
            self.degraded_engines.add(engine_name)
            return {
                "engine": engine_name,
                "status": "degraded",
                "score": 0.5,
                "confidence": 0.0,
                "labels": ["engine_failure"],
                "reason": f"Engine {engine_name} failed: {str(e)}",
                "error": str(e)
            }

    def get_safe_decision(self, final_score: float) -> str:
        if self.safe_mode and self.integrity_failures:
            logger.error("Integrity failures present - forcing block")
            return "block"

        if self.safe_mode:
            if self.degraded_engines:
                return "challenge"

        if final_score >= 0.8:
            return "block"
        elif final_score >= 0.6:
            return "challenge"
        elif final_score >= 0.3:
            return "monitor"
        else:
            return "allow"


    def enable_safe_mode(self, reason: str):
        """Activate safe mode, typically due to integrity failure."""
        self.safe_mode = True
        logger.critical(f"Safe mode enabled: {reason}")

    def reset_breaker(self, engine_name: str):
        breaker = _get_breaker(engine_name)
        breaker.state = "CLOSED"
        breaker.failures = 0
        logger.info(f"Circuit breaker for {engine_name} manually reset")

    def get_status(self) -> dict:
        status = {}
        for name in set(list(_health_registry.keys()) + list(_breaker_registry.keys())):
            health = _health_registry.get(name)
            breaker = _breaker_registry.get(name)
            status[name] = {
                "health_state": health.state if health else "unknown",
                "breaker_state": breaker.state if breaker else "closed",
                "consecutive_failures": health.consecutive_failures if health else 0,
                "degraded": name in self.degraded_engines
            }
        return status

fallback = FallbackManager()
# === Phase 5 signed artifact strategy ===
# Signed manifest with HMAC-SHA256 validation at startup via verify_critical_artifacts()
