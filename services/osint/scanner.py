# FILE: services/osint/scanner.py
from typing import Dict, Any, List, Optional
import tldextract

from .adapters import (
    WhoisAdapter, DnsAdapter, SslLabsAdapter, SecurityHeadersAdapter,
    RobotsAdapter, SocialLinksAdapter, EmailBasicAdapter
)


class OsintScanner:
    """Одноразовий збір пасивних сигналів по домену/сайту/e-mail."""
    
    def __init__(self, url: Optional[str] = None, domain: Optional[str] = None, email: Optional[str] = None):
        self.url = (url or "").strip()
        self.domain = (domain or "").strip().lower()
        self.email = (email or "").strip()

        if not self.domain and self.url:
            ex = tldextract.extract(self.url)
            if ex.domain and ex.suffix:
                self.domain = f"{ex.domain}.{ex.suffix}"

    def run_all(self) -> List[Dict[str, Any]]:
        target = {"url": self.url, "domain": self.domain, "email": self.email}
        adapters = [
            WhoisAdapter(target),
            DnsAdapter(target),
            SslLabsAdapter(target),
            SecurityHeadersAdapter(target),
            RobotsAdapter(target),
            SocialLinksAdapter(target),
            EmailBasicAdapter(target),
        ]
        results: List[Dict[str, Any]] = []
        for a in adapters:
            res = a.run()
            res["service"] = a.name
            results.append(res)
        return results
