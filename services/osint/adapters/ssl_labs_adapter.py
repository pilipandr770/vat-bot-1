# FILE: services/osint/adapters/ssl_labs_adapter.py
from typing import Dict, Any
import time
import requests
from ..base import OsintAdapter


class SslLabsAdapter(OsintAdapter):
    name = "ssl_labs"

    API = "https://api.ssllabs.com/api/v3/analyze"

    def run(self) -> Dict[str, Any]:
        domain = (self.target.get("domain") or "").strip().lower()
        if not domain:
            return {"status": "error", "data": {}, "notes": "domain is empty"}

        try:
            # Старт аналізу
            r = requests.get(self.API, params={"host": domain, "publish": "off", "fromCache": "on"}, timeout=10)
            r.raise_for_status()
            payload = r.json()

            # Якщо в кеші немає — ініціюємо і чекаємо кілька циклів (легке очікування)
            attempts = 0
            while payload.get("status") in {"DNS", "IN_PROGRESS"} and attempts < 6:
                time.sleep(5)
                r = requests.get(self.API, params={"host": domain, "publish": "off"}, timeout=10)
                payload = r.json()
                attempts += 1

            endpoints = payload.get("endpoints", []) or []
            grade = endpoints[0].get("grade") if endpoints else None
            data = {"status_raw": payload.get("status"), "grade": grade, "endpoints": len(endpoints)}
            status = "ok" if grade else "warn"
            notes = "" if grade else "No grade returned"
            return {"status": status, "data": data, "notes": notes}
        except Exception as e:
            return {"status": "warn", "data": {}, "notes": f"SSL Labs error: {e}"}
