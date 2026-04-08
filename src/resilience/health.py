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

def get_runtime_health_snapshot():
    """Return health status of engines, DB, Redis."""
    from src.core.fallback import _health_registry, fallback
    engines = {}
    for name, health in _health_registry.items():
        engines[name] = health.state if health.state != "tripped" else "unhealthy"
    # Add DB/Redis health checks (simple placeholders)
    db_healthy = True   # You can implement actual DB ping
    redis_healthy = True
    return {
        "status": "ok" if all(v != "unhealthy" for v in engines.values()) and db_healthy and redis_healthy else "degraded",
        "engines": engines,
        "db": "healthy" if db_healthy else "unhealthy",
        "redis": "healthy" if redis_healthy else "unhealthy"
    }