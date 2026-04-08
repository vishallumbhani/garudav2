import asyncio
import random
from functools import wraps
from typing import Callable

async def retry_async(func: Callable, max_attempts=2, base_delay=0.5, jitter=True):
    """Retry async function on exception, with exponential backoff."""
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return await func()
        except Exception as e:
            last_exc = e
            if attempt == max_attempts - 1:
                raise
            delay = base_delay * (2 ** attempt)
            if jitter:
                delay *= random.uniform(0.8, 1.2)
            await asyncio.sleep(delay)
    raise last_exc