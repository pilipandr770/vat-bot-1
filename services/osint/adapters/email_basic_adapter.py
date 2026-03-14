# FILE: services/osint/adapters/email_basic_adapter.py
from typing import Dict, Any
from email_validator import validate_email, EmailNotValidError
from ..base import OsintAdapter


class EmailBasicAdapter(OsintAdapter):
    name = "email_basic"

    def run(self) -> Dict[str, Any]:
        email = (self.target.get("email") or "").strip()
        if not email:
            return {"status": "error", "data": {}, "notes": "email empty"}
        try:
            info = validate_email(email, check_deliverability=False)
            data = {
                "email": info.email,
                "domain": info.domain,
                "local_part": info.local_part,
                "ascii_email": info.ascii_email,
            }
            return {"status": "ok", "data": data, "notes": ""}
        except EmailNotValidError as e:
            return {"status": "warn", "data": {"email": email}, "notes": f"invalid format: {e}"}
