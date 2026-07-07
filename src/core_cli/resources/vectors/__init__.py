"""Consumer vector-store commands."""

from __future__ import annotations

from . import query, rebuild, status, sync, sync_code
from .hub import app

__all__ = ["app"]
