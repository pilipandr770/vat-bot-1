"""
Rate limiting service for API and web endpoints.
Prevents DDoS attacks and API abuse.

Backend selection:
  - If REDIS_URL is set in Flask config, uses Redis (consistent across workers).
  - Otherwise falls back to in-process dict (safe for single-worker dev mode).
"""
import time
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from flask import request, session, current_app
from functools import wraps
import logging

logger = logging.getLogger(__name__)


def _get_redis():
    """Return a Redis client if configured, else None."""
    try:
        import redis
        from flask import current_app
        url = current_app.config.get('REDIS_URL') or current_app.config.get('CELERY_BROKER_URL')
        if url:
            return redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
    except Exception:
        pass
    return None


class RedisRateLimiter:
    """Redis-backed rate limiter — consistent across multiple gunicorn workers."""

    def _key(self, identifier: str, window: int) -> str:
        slot = int(time.time()) // window
        return f"ratelimit:{identifier}:{window}:{slot}"

    def is_allowed(self, identifier: str, limit: int, window: int) -> Tuple[bool, Dict]:
        try:
            r = _get_redis()
            if r is None:
                raise RuntimeError("Redis not available")
            key = self._key(identifier, window)
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, window * 2)
            current_count, _ = pipe.execute()
            current_count = int(current_count)
            allowed = current_count <= limit
            retry_after = window - (int(time.time()) % window) if not allowed else 0
            return allowed, {
                'current_count': current_count,
                'limit': limit,
                'retry_after': retry_after,
            }
        except Exception as e:
            logger.warning(f"RedisRateLimiter error, falling back: {e}")
            return True, {'current_count': 0, 'limit': limit, 'retry_after': 0}

    def get_status(self, identifier: str, limit: int, window: int) -> Dict:
        try:
            r = _get_redis()
            if r is None:
                raise RuntimeError
            key = self._key(identifier, window)
            current_count = int(r.get(key) or 0)
            remaining = max(0, limit - current_count)
            reset = (int(time.time()) // window + 1) * window
            return {'limit': limit, 'remaining': remaining, 'reset': reset, 'retry_after': 0}
        except Exception:
            return {'limit': limit, 'remaining': limit, 'reset': int(time.time()) + window, 'retry_after': 0}

    def _get_identifier(self, use_session=True) -> str:
        if use_session and 'user_id' in session:
            return f"user_{session['user_id']}"
        return f"ip_{request.remote_addr}"


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


class _SmartRateLimiter:
    """Proxy that routes to Redis when available, in-memory otherwise."""

    def __init__(self):
        self._mem = RateLimiter()
        self._redis = RedisRateLimiter()

    def _backend(self):
        try:
            if _get_redis():
                return self._redis
        except Exception:
            pass
        return self._mem

    def is_allowed(self, identifier, limit, window):
        return self._backend().is_allowed(identifier, limit, window)

    def get_status(self, identifier, limit, window):
        return self._backend().get_status(identifier, limit, window)

    def _get_identifier(self, use_session=True):
        return self._mem._get_identifier(use_session)


# Global rate limiter instance — Redis-backed when REDIS_URL is set, else in-memory
rate_limiter = _SmartRateLimiter()


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


def auth_rate_limit(requests_per_minute: int = 5, requests_per_hour: int = 20):
    """
    Decorator for HTML auth endpoints (login, register, password reset).
    Redirects back with a flash message instead of returning JSON on limit exceeded.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method != 'POST':
                return f(*args, **kwargs)

            identifier = f"ip_{request.remote_addr}"

            allowed_minute, info_minute = rate_limiter.is_allowed(identifier, requests_per_minute, 60)
            if not allowed_minute:
                logger.warning(f"Auth brute-force blocked for {identifier} on {request.path}")
                from flask import flash, redirect
                flash(
                    f'Zu viele Versuche. Bitte warten Sie {info_minute["retry_after"]} Sekunden.',
                    'error'
                )
                return redirect(request.url)

            allowed_hour, info_hour = rate_limiter.is_allowed(identifier, requests_per_hour, 3600)
            if not allowed_hour:
                logger.warning(f"Auth hourly limit blocked for {identifier} on {request.path}")
                from flask import flash, redirect
                flash('Stundenlimit für Anmeldeversuche erreicht. Bitte versuchen Sie es später erneut.', 'error')
                return redirect(request.url)

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
