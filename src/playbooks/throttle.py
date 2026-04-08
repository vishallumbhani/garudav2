import time
from collections import defaultdict
from typing import Dict, Tuple

# Simple in-memory rate limiter (replace with Redis for production)
_request_counts: Dict[str, list] = defaultdict(list)  # session_id -> list of timestamps

def is_throttled(session_id: str, limit: int = 60, window_seconds: int = 60) -> Tuple[bool, int]:
    """
    Returns (is_throttled, remaining_requests_in_window).
    If throttled, the session should be slowed or blocked.
    """
    now = time.time()
    # Clean old entries
    timestamps = _request_counts[session_id]
    timestamps = [ts for ts in timestamps if now - ts < window_seconds]
    _request_counts[session_id] = timestamps

    if len(timestamps) >= limit:
        return True, 0

    # Record this request
    timestamps.append(now)
    remaining = limit - len(timestamps)
    return False, remaining

def reset_throttle(session_id: str) -> None:
    _request_counts.pop(session_id, None)