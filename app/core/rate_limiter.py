"""Rate limiting implementation."""
import time
from collections import defaultdict
from typing import ClassVar


class RateLimiter:
    """Simple in-memory rate limiter using token bucket algorithm."""

    def __init__(self, requests: int, period_seconds: int):
        """
        Initialize rate limiter.

        Args:
            requests: Number of requests allowed
            period_seconds: Time period in seconds
        """
        self.requests = requests
        self.period_seconds = period_seconds
        self.clients: ClassVar[dict[str, list[float]]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check if client is allowed to make a request."""
        now = time.time()
        cutoff = now - self.period_seconds

        # Clean old timestamps
        if client_id in self.clients:
            self.clients[client_id] = [ts for ts in self.clients[client_id] if ts > cutoff]
        else:
            self.clients[client_id] = []

        # Check if allowed
        if len(self.clients[client_id]) < self.requests:
            self.clients[client_id].append(now)
            return True
        return False

    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client."""
        now = time.time()
        cutoff = now - self.period_seconds

        if client_id in self.clients:
            requests_in_window = len(
                [ts for ts in self.clients[client_id] if ts > cutoff],
            )
            return max(0, self.requests - requests_in_window)
        return self.requests
