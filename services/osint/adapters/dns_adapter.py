# FILE: services/osint/adapters/dns_adapter.py
from typing import Dict, Any, List
from ..base import OsintAdapter

try:
    import dns.resolver  # dnspython
except Exception:
    dns = None


class DnsAdapter(OsintAdapter):
    name = "dns"

    def _q(self, record: str) -> List[str]:
        out = []
        try:
            for r in dns.resolver.resolve(self.target["domain"], record, lifetime=3.0):
                out.append(r.to_text())
        except Exception:
            pass
        return out

    def run(self) -> Dict[str, Any]:
        domain = (self.target.get("domain") or "").strip().lower()
        if not domain:
            return {"status": "error", "data": {}, "notes": "domain is empty"}
        if dns is None:
            return {"status": "error", "data": {}, "notes": "dnspython not installed"}

        data = {
            "A": self._q("A"),
            "AAAA": self._q("AAAA"),
            "MX": self._q("MX"),
            "NS": self._q("NS"),
            "TXT": self._q("TXT"),
        }
        status = "ok"
        notes = ""
        # Простий сигнал: якщо нема MX — часто це мінус для бізнес-домену
        if not data["MX"]:
            status = "warn"
            notes = "No MX records found"
        return {"status": status, "data": data, "notes": notes}
