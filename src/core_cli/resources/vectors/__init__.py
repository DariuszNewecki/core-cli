"""Consumer vector-store commands."""

from __future__ import annotations

from . import (  # noqa: F401
    query,
    rebuild,
    status,
    sync,
    sync_code,
)
from .hub import app


__all__ = ["app"]
