import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Use your existing threat_memory or a simple in-memory set
# For now, we'll use a simple in-memory set (replace with Redis if needed)
_isolated_sessions = set()

def isolate_session(session_id: str, reason: str, duration_seconds: int = 3600) -> None:
    """Mark a session as isolated. Subsequent requests from this session will be treated as hostile."""
    _isolated_sessions.add(session_id)
    logger.warning(f"Session {session_id} isolated: {reason}")
    # TODO: If using Redis, store with TTL = duration_seconds

def is_session_isolated(session_id: str) -> bool:
    return session_id in _isolated_sessions

def release_session(session_id: str) -> None:
    _isolated_sessions.discard(session_id)