# FILE: services/osint/adapters/whois_adapter.py
from typing import Dict, Any
from ..base import OsintAdapter

try:
    import whois  # python-whois
except Exception:
    whois = None


class WhoisAdapter(OsintAdapter):
    name = "whois"

    def run(self) -> Dict[str, Any]:
        domain = (self.target.get("domain") or "").strip().lower()
        if not domain:
            return {"status": "error", "data": {}, "notes": "domain is empty"}

        if whois is None:
            return {"status": "error", "data": {}, "notes": "python-whois not installed"}

        try:
            w = whois.whois(domain)
            data = {
                "domain_name": getattr(w, "domain_name", None),
                "registrar": getattr(w, "registrar", None),
                "creation_date": str(getattr(w, "creation_date", None)),
                "expiration_date": str(getattr(w, "expiration_date", None)),
                "updated_date": str(getattr(w, "updated_date", None)),
                "status": getattr(w, "status", None),
                "name_servers": getattr(w, "name_servers", None),
            }
            return {"status": "ok", "data": data, "notes": ""}
        except Exception as e:
            return {"status": "warn", "data": {}, "notes": f"whois error: {e}"}
