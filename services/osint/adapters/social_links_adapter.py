# FILE: services/osint/adapters/social_links_adapter.py
from typing import Dict, Any, List
import re
import requests
from bs4 import BeautifulSoup
from ..base import OsintAdapter

SOCIAL_DOMAINS = ("linkedin.com", "facebook.com", "instagram.com", "youtube.com", "t.me", "x.com", "twitter.com")


class SocialLinksAdapter(OsintAdapter):
    name = "social_links"

    def run(self) -> Dict[str, Any]:
        url = self.target.get("url") or ""
        if not url:
            domain = (self.target.get("domain") or "").strip().lower()
            if domain:
                url = f"https://{domain}"
        if not url:
            return {"status": "error", "data": {}, "notes": "url/domain is empty"}

        try:
            r = requests.get(url, timeout=6)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            links = [a.get("href") for a in soup.find_all("a", href=True)]
            socials: List[str] = []
            for l in links:
                if any(s in l for s in SOCIAL_DOMAINS):
                    socials.append(l)
            socials = sorted(set(socials))
            status = "ok" if socials else "warn"
            notes = "" if socials else "no social links found"
            return {"status": status, "data": {"links": socials}, "notes": notes}
        except Exception as e:
            return {"status": "warn", "data": {}, "notes": f"social error: {e}"}
