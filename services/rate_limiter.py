"""
Rate limiting service for API and web endpoints.
Prevents DDoS attacks and API abuse.
"""
import time
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from flask import request, session
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """In-memory rate limiter with configurable limits per user/IP."""

    def __init__(self):
        self.requests = {}  # {identifier: [(timestamp, endpoint), ...]}
        self.cleanup_interval = 300  # Cleanup every 5 minutes
        self.last_cleanup = time.time()

    def _get_identifier(self, use_session=True) -> str:
        """Get unique identifier for rate limiting (user_id or IP)."""
        if use_session and 'user_id' in session:
            return f"user_{session['user_id']}"
        return f"ip_{request.remote_addr}"

    def _cleanup_old_entries(self):
        """Remove old entries to prevent memory bloat."""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return

        cutoff_time = now - 3600  # Keep 1 hour of history
        for identifier in list(self.requests.keys()):
            # Keep only recent requests
            self.requests[identifier] = [
                (ts, ep) for ts, ep in self.requests[identifier]
                if ts > cutoff_time
            ]
            # Remove empty entries
            if not self.requests[identifier]:
                del self.requests[identifier]

        self.last_cleanup = now

    def is_allowed(self, identifier: str, limit: int, window: int) -> Tuple[bool, Dict]:
        """
        Check if request is allowed within rate limit.

        Args:
            identifier: Unique identifier (user_id or IP)
            limit: Max requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (is_allowed, info_dict)
        """
        self._cleanup_old_entries()

        now = time.time()
        cutoff = now - window

        # Get requests in current window
        if identifier not in self.requests:
            self.requests[identifier] = []

        recent_requests = [
            (ts, ep) for ts, ep in self.requests[identifier]
            if ts > cutoff
        ]
        self.requests[identifier] = recent_requests

        # Get endpoint for logging
        endpoint = request.endpoint or 'unknown'

        # Record this request
        self.requests[identifier].append((now, endpoint))

        allowed = len(recent_requests) < limit
        reset_time = int(cutoff + window) if recent_requests else int(now + window)

        info = {
            'limit': limit,
            'remaining': max(0, limit - len(recent_requests) - 1),
            'reset': reset_time,
            'retry_after': max(0, reset_time - int(now)),
            'current_count': len(recent_requests) + 1
        }

        return allowed, info

    def get_status(self, identifier: str, limit: int, window: int) -> Dict:
        """Get current rate limit status without incrementing."""
        now = time.time()
        cutoff = now - window

        if identifier not in self.requests:
            return {'limit': limit, 'remaining': limit, 'reset': int(now + window), 'retry_after': 0}

        recent = [ts for ts, _ in self.requests[identifier] if ts > cutoff]
        reset_time = int(cutoff + window) if recent else int(now + window)

        return {
            'limit': limit,
            'remaining': max(0, limit - len(recent)),
            'reset': reset_time,
            'retry_after': max(0, reset_time - int(now))
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(requests_per_minute: int = 60, requests_per_hour: int = 1000):
    """
    Decorator for rate limiting endpoints.

    Args:
        requests_per_minute: Max requests per minute (default 60)
        requests_per_hour: Max requests per hour (default 1000)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            identifier = rate_limiter._get_identifier(use_session=True)

            # Check per-minute limit
            allowed_minute, info_minute = rate_limiter.is_allowed(
                identifier, requests_per_minute, 60
            )

            if not allowed_minute:
                logger.warning(
                    f"Rate limit exceeded (per minute) for {identifier}: "
                    f"{info_minute['current_count']} requests in 60s"
                )
                return {
                    'success': False,
                    'error': f'Sie haben zu viele Anfragen gestellt. '
                             f'Bitte warten Sie {info_minute["retry_after"]} Sekunden bevor Sie es erneut versuchen.',
                    'retry_after': info_minute['retry_after']
                }, 429

            # Check per-hour limit
            allowed_hour, info_hour = rate_limiter.is_allowed(
                identifier, requests_per_hour, 3600
            )

            if not allowed_hour:
                logger.warning(
                    f"Rate limit exceeded (per hour) for {identifier}: "
                    f"{info_hour['current_count']} requests in 3600s"
                )
                return {
                    'success': False,
                    'error': f'Stundenlimit erreicht. '
                             f'Bitte versuchen Sie es in {info_hour["retry_after"]} Sekunden erneut.',
                    'retry_after': info_hour['retry_after']
                }, 429

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def get_rate_limit_headers(identifier: str, limit: int, window: int) -> Dict[str, str]:
    """Generate rate limit headers for response."""
    status = rate_limiter.get_status(identifier, limit, window)
    return {
        'X-RateLimit-Limit': str(status['limit']),
        'X-RateLimit-Remaining': str(status['remaining']),
        'X-RateLimit-Reset': str(status['reset']),
        'X-RateLimit-RetryAfter': str(status['retry_after'])
    }
