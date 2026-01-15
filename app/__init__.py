"""App package exports."""
from application import create_app  # re-export for legacy import locations

__all__ = ["create_app"]