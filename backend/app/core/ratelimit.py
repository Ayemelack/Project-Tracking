"""In-memory sliding-window rate limiting for authentication endpoints.

Single-process only: state lives in this process and resets on restart or when
the key cap is reached. This matches the single-worker uvicorn deployment this
application uses; it intentionally avoids a distributed store dependency.
"""

import threading
import time
from collections import defaultdict, deque

MAX_KEYS = 20000
MAX_TRACKED_PER_KEY = 128


class SlidingWindowRateLimiter:
    def __init__(self):
        self._lock = threading.Lock()
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def _prune_locked(self, key: str, window_seconds: float) -> None:
        bucket = self._buckets[key]
        cutoff = time.monotonic() - window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        # Keep memory bounded even if a key is mis-handled upstream.
        while len(bucket) > MAX_TRACKED_PER_KEY:
            bucket.popleft()

    def allow(self, key: str, max_requests: int, window_seconds: float) -> bool:
        """Record an attempt and return True if it is within the rate limit."""
        with self._lock:
            if key not in self._buckets and len(self._buckets) >= MAX_KEYS:
                self._buckets.clear()
            self._prune_locked(key, window_seconds)
            bucket = self._buckets[key]
            if len(bucket) >= max_requests:
                return False
            bucket.append(time.monotonic())
            return True

    def clear(self, key: str) -> None:
        with self._lock:
            self._buckets.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


rate_limiter = SlidingWindowRateLimiter()