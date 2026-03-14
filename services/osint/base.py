# FILE: services/osint/base.py
import abc
from typing import Any, Dict


class OsintAdapter(abc.ABC):
    """Базовий адаптер для OSINT-перевірок."""
    name: str = "base"

    def __init__(self, target: Dict[str, Any]) -> None:
        """
        target = {
          "domain": str | None,
          "url": str | None,
          "email": str | None
        }
        """
        self.target = target

    @abc.abstractmethod
    def run(self) -> Dict[str, Any]:
        """Повертає структуру: {"status": "ok|warn|error", "data": {...}, "notes": "..."}"""
        ...
