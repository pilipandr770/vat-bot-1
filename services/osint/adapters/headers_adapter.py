# FILE: services/osint/adapters/headers_adapter.py
from typing import Dict, Any
import requests
from ..base import OsintAdapter

SEC_KEYS = [
    "content-security-policy",
    "strict-transport-security",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
    "permissions-policy",
]


class SecurityHeadersAdapter(OsintAdapter):
    name = "security_headers"

    def run(self) -> Dict[str, Any]:
        url = self.target.get("url") or ""
        if not url:
            domain = (self.target.get("domain") or "").strip().lower()
            if domain:
                url = f"https://{domain}"
        if not url:
            return {"status": "error", "data": {}, "notes": "url/domain is empty"}

        try:
            r = requests.get(url, timeout=6, allow_redirects=True)
            r.raise_for_status()
            headers = {k.lower(): v for k, v in r.headers.items()}
            present = {k: headers.get(k) for k in SEC_KEYS}
            missing = [k for k, v in present.items() if v is None]
            status = "ok" if not missing else "warn"
            notes = "" if not missing else f"Missing headers: {', '.join(missing)}"
            return {"status": status, "data": {"headers": present}, "notes": notes}
        except Exception as e:
            return {"status": "warn", "data": {}, "notes": f"headers error: {e}"}
