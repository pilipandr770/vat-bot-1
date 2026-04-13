"""Security helpers for CSRF-exempt JSON endpoints."""
from functools import wraps
from urllib.parse import urlparse

from flask import current_app, jsonify, request


def require_same_origin(f):
    """
    Reject cross-origin POST requests.

    Use on CSRF-exempt JSON endpoints to prevent cross-site request forgery
    without requiring a CSRF token in the request body.

    Browsers always include an Origin (or Referer) header on cross-origin
    POSTs; its absence on a POST is therefore suspicious and is also blocked.

    Same-origin requests (Origin header matches the server host) pass through.
    Additional allowed origins can be configured via ALLOWED_ORIGINS config key
    (comma-separated list of hostnames, e.g. ``example.com,staging.example.com``).
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method != 'POST':
            return f(*args, **kwargs)

        origin = request.headers.get('Origin') or request.headers.get('Referer')

        if not origin:
            # Browsers MUST send Origin on cross-origin POST requests.
            # Missing Origin on POST = non-browser client or stripped header.
            # Block to prevent simple CSRF gadgets.
            current_app.logger.warning(
                'Blocked POST without Origin header to %s', request.path
            )
            return jsonify({'error': 'Origin header required'}), 403

        try:
            origin_host = urlparse(origin).netloc.lower()
        except Exception:
            return jsonify({'error': 'Invalid Origin header'}), 403

        # Build set of allowed hosts
        server_host = urlparse(request.host_url).netloc.lower()
        allowed: set[str] = {server_host}
        extra = current_app.config.get('ALLOWED_ORIGINS', '')
        if extra:
            allowed.update(h.strip().lower() for h in extra.split(',') if h.strip())

        if origin_host not in allowed:
            current_app.logger.warning(
                'Blocked cross-origin POST to %s from origin %s',
                request.path, origin_host
            )
            return jsonify({'error': 'Cross-origin request blocked'}), 403

        return f(*args, **kwargs)

    return wrapper
