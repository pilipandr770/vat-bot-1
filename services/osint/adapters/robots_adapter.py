# FILE: services/osint/adapters/robots_adapter.py
from typing import Dict, Any
import requests
from ..base import OsintAdapter


class RobotsAdapter(OsintAdapter):
    name = "robots_sitemap"

    def run(self) -> Dict[str, Any]:
        domain = (self.target.get("domain") or "").strip().lower()
        if not domain:
            return {"status": "error", "data": {}, "notes": "domain is empty"}

        base = f"https://{domain}"
        out = {"robots_txt": None, "sitemaps": []}
        notes = ""
        try:
            r = requests.get(f"{base}/robots.txt", timeout=5)
            if r.status_code == 200 and "Disallow" in r.text:
                out["robots_txt"] = "present"
            else:
                out["robots_txt"] = "missing"
        except Exception:
            out["robots_txt"] = "error"

        # Пробуємо типові шляхи sitemap
        for path in ("/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"):
            try:
                r = requests.get(f"{base}{path}", timeout=5)
                if r.status_code == 200 and ("<urlset" in r.text or "<sitemapindex" in r.text):
                    out["sitemaps"].append(path)
            except Exception:
                pass

        status = "ok" if out["robots_txt"] == "present" or out["sitemaps"] else "warn"
        if status == "warn":
            notes = "No robots.txt or sitemap.xml detected"
        return {"status": status, "data": out, "notes": notes}
