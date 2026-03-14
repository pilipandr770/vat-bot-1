# FILE: services/osint/adapters/ssl_labs_adapter.py
from typing import Dict, Any
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
            # Спочатку перевіряємо кеш
            r = requests.get(
                self.API, 
                params={"host": domain, "publish": "off", "fromCache": "on", "all": "done"}, 
                timeout=10
            )
            r.raise_for_status()
            payload = r.json()

            # Якщо в кеші є результат - повертаємо одразу
            if payload.get("status") == "READY":
                endpoints = payload.get("endpoints", []) or []
                grade = endpoints[0].get("grade") if endpoints else None
                data = {
                    "status_raw": payload.get("status"), 
                    "grade": grade, 
                    "endpoints": len(endpoints),
                    "cached": True
                }
                status = "ok" if grade else "warn"
                notes = "from cache" if grade else "No grade in cache"
                return {"status": status, "data": data, "notes": notes}
            
            # Якщо кешу немає - повертаємо "pending" замість очікування
            if payload.get("status") in {"DNS", "IN_PROGRESS"}:
                return {
                    "status": "warn", 
                    "data": {"status_raw": payload.get("status"), "pending": True}, 
                    "notes": f"SSL Labs analysis in progress ({payload.get('status')}). Check later for results."
                }
            
            # Якщо статус ERROR або інший
            return {
                "status": "warn", 
                "data": {"status_raw": payload.get("status")}, 
                "notes": f"Unexpected status: {payload.get('status')}"
            }
            
        except requests.Timeout:
            return {"status": "warn", "data": {}, "notes": "SSL Labs API timeout"}
        except Exception as e:
            return {"status": "warn", "data": {}, "notes": f"SSL Labs error: {str(e)[:100]}"}
